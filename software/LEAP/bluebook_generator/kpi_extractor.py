import os
import re
from typing import List, Dict, Tuple, Any

# Scanner performance knobs
IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".agents",
    ".codex",
    "node_modules",
    "dist",
    "build",
    "_build",
    "_sources",
    "_static",
    "docs",
    "bluebook_generator",
    "templates",
    "htmlcov",
    "__pycache__",
    "site-packages",
    ".venv",
    "venv",
    "env",
    "virtualenv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "ai_bluebook_generator.egg-info",
}
IGNORE_DIR_SUFFIXES = {
    "_env",
    "-env",
    ".env",
    "_venv",
    "-venv",
}
IGNORE_DIR_PARTS = {
    "site-packages",
    "dist-packages",
}
IGNORE_FILES = {
    "app.py",
    "run_generation.py",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "USAGE.md",
}
ALLOWED_EXTS = {
    ".py",
    ".sql",
    ".ps1",
    ".dax",
    ".cs",
    ".vb",
    ".abap",
    ".st",
    ".hdbview",
    ".hdbprocedure",
    ".hdbfunction",
    ".hdbtablefunction",
    ".sqlscript",
    ".tsql",
    ".pks",
    ".pkb",
    ".pls",
    ".txt",
    ".csv",
}
# Extensions to skip entirely (no KPI extraction, not counted)
IGNORE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".svg",
    ".ico",
    ".tiff",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
}
MAX_FILE_MB = float(os.environ.get("KPI_MAX_FILE_MB", "2"))  # default 2 MB

# Optional formula extraction from comments like "Formula: ..."
try:
    from .parser import extract_formula_from_comments as _extract_formula_from_comments
except Exception:
    _extract_formula_from_comments = None

__all__ = ["find_kpis_in_directory"]


def _empty_scan_stats() -> Dict[str, Any]:
    return {
        "filesystem_files": 0,
        "filesystem_dirs": 0,
        "filesystem_items": 0,
        "filesystem_bytes": 0,
        "files_after_directory_exclusions": 0,
        "files_scanned": 0,
        "lines_analyzed": 0,
        "skipped_binary_files": 0,
        "ignored_dirs": 0,
        "ignored_files": 0,
        "unsupported_files": 0,
        "oversized_files": 0,
        "empty_or_unreadable_files": 0,
        "filtered_non_kpi_candidates": 0,
        "candidate_review": [],
    }


def _count_filesystem_inventory(base: str) -> Dict[str, int]:
    """Count every file and directory under the selected folder before scan filters."""
    files = 0
    dirs = 0
    total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(base, onerror=lambda _: None):
        dirs += len(dirnames)
        files += len(filenames)
        for fn in filenames:
            try:
                total_bytes += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return {
        "filesystem_files": files,
        "filesystem_dirs": dirs,
        "filesystem_items": files + dirs,
        "filesystem_bytes": total_bytes,
    }


# ---------- Supported extensions (language hint) ----------

_SUPPORTED_EXTS = {
    # Python
    ".py": "python",
    # .NET family
    ".cs": "csharp",
    ".vb": "vbnet",
    # SQL families (ANSI SQL, T-SQL, Oracle/PLSQL, HANA SQLScript)
    ".sql": "sql",
    ".tsql": "tsql",  # T‑SQL specific files
    ".pks": "plsql",
    ".pkb": "plsql",
    ".pls": "plsql",
    # SAP HANA SQLScript artifacts
    ".hdbprocedure": "hana",
    ".hdbfunction": "hana",
    ".hdbview": "hana",
    ".hdbtablefunction": "hana",
    ".sqlscript": "hana",
    # SAP ABAP
    ".abap": "abap",
    # Power BI DAX (text exports)
    ".dax": "dax",
    ".dax.txt": "dax",
    # IEC 61131‑3 Structured Text / PLC textual files
    ".st": "iec_st",
    ".scl": "iec_st",  # Siemens SCL
    ".awl": "iec_st",  # STL/AWL textual
    # Generic text/CSV exports (Excel/BI/SAP dumps)
    ".txt": "text",
    ".csv": "csv",
}


# ---------- Utilities ----------


def _read_text_file_safe(path: str, max_bytes: int = 2_000_000) -> str:
    """Read small text files safely; skip very large or unreadable files."""
    try:
        if os.path.getsize(path) > max_bytes:
            return ""
    except Exception:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _window(lines: List[str], center: int, before: int = 10, after: int = 20) -> str:
    """Return a small window of text lines around a center line number."""
    start = max(0, center - before)
    end = min(len(lines), center + after + 1)
    return "\n".join(lines[start:end])


def _expand_forward_statement(
    lines: List[str], start_index: int, back: int = 5, max_forward: int = 200
) -> str:
    """Return a forward-expanded SQL-ish statement context starting a few lines before start_index.

    - Includes up to `back` lines before the start_index for context.
    - Scans forward up to `max_forward` lines or until a likely statement terminator is seen:
      semicolon at low parenthesis depth, a lone GO, or end of file.
    - Works for SQL/T-SQL/PLSQL/HANA snippets where KPI comment precedes a CREATE/SELECT.
    """
    import re as _re

    n = len(lines)
    if n == 0:
        return ""

    start = max(0, min(start_index, n - 1))
    ctx_start = max(0, start - back)

    end = start
    depth = 0
    for j in range(start, min(n, start + max_forward)):
        line = lines[j].rstrip("\n")
        end = j
        # Track parentheses depth to avoid stopping too early inside CAST(...), CASE(...), etc.
        depth += line.count("(") - line.count(")")
        if _re.search(r";\s*$", line) and depth <= 0:
            break
        if _re.match(r"^\s*GO\s*$", line, _re.I):
            break
        if _re.match(
            r"^\s*/\s*$", line
        ):  # Oracle '/' statement separator on its own line
            break

    return "\n".join(line.rstrip("\n") for line in lines[ctx_start : end + 1])


def _normalize_name(raw: str) -> str:
    name = (raw or "").strip()
    if len(name) >= 2 and (
        (name[0], name[-1]) in {("[", "]"), ("(", ")"), ('"', '"'), ("'", "'")}
    ):
        name = name[1:-1].strip()
    else:
        name = name.strip("\"'")
    name = re.sub(r"[_\s]+", " ", name)
    return name


BUSINESS_KPI_MARKERS = {
    "availability",
    "capacity",
    "complaint",
    "conversion",
    "cost",
    "covariance",
    "efficiency",
    "emission",
    "emissions",
    "intensity",
    "inventory",
    "kpi",
    "leakage",
    "loss",
    "margin",
    "metric",
    "oee",
    "percentage",
    "profit",
    "purity",
    "rate",
    "ratio",
    "recovery",
    "revenue",
    "score",
    "selectivity",
    "spend",
    "throughput",
    "utilization",
    "variance",
    "yield",
}

STRICT_FUNCTION_BLACKLIST = re.compile(
    r"(?ix)"
    r"(^|[_\s-])test([_\s-]|$)|"
    r"(^|[_\s-])mock([_\s-]|$)|"
    r"(^|[_\s-])fixture([_\s-]|$)|"
    r"(^|[_\s-])render([_\s-]|$)|"
    r"(^|[_\s-])visit([_\s-]|$)|"
    r"(^|[_\s-])decorate|decoration|"
    r"(^|[_\s-])wrapper([_\s-]|$)|"
    r"(^|[_\s-])configuration([_\s-]|$)|"
    r"(^|[_\s-])declaration([_\s-]|$)|"
    r"(^|[_\s-])expiration([_\s-]|$)|"
    r"(^|[_\s-])cookie([_\s-]|$)|"
    r"(^|[_\s-])session([_\s-]|$)"
)


def _is_ignored_dir_name(name: str) -> bool:
    lowered = (name or "").lower()
    return (
        lowered in IGNORE_DIRS
        or lowered.startswith(".")
        or lowered.endswith(".egg-info")
        or lowered in IGNORE_DIR_PARTS
        or any(lowered.endswith(suffix) for suffix in IGNORE_DIR_SUFFIXES)
    )


def _has_business_marker(text: str) -> bool:
    lowered = (text or "").lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered)
    words = set(normalized.split())
    if words & BUSINESS_KPI_MARKERS:
        return True
    # Preserve common compact naming conventions such as l1_ratio or spendLeakagePct.
    compact = re.sub(r"[^a-z0-9]+", "", lowered)
    return any(marker in compact for marker in BUSINESS_KPI_MARKERS if len(marker) >= 4)


def _has_formula_with_business_shape(text: str) -> bool:
    source = _strip_string_literals(text or "")
    has_operator = bool(re.search(r"[+\-*/×÷]", source))
    has_aggregate = bool(re.search(r"(?i)\b(SUM|AVG|COUNT|MIN|MAX|mean|average|total)\s*\(", source))
    has_alias_metric = bool(
        re.search(
            r"(?i)\bAS\s+[A-Za-z_][A-Za-z0-9_]*(?:_pct|_percent|_percentage|_ratio|_rate|_yield|_intensity|_score|_variance|_cost|_leakage)\b",
            source,
        )
    )
    return has_operator and (has_aggregate or has_alias_metric or _has_business_marker(source))


def _has_explicit_formula_marker(text: str) -> bool:
    return bool(
        re.search(
            r"(?im)^\s*(?:#|--|//|/\*|\*|'|REM\b)?\s*(?:business\s+formula|formula|calculation|computes|body\s+computes|body\s+hint)\s*:",
            text or "",
        )
    )


def _has_explicit_business_metadata(text: str) -> bool:
    return bool(
        re.search(
            r"(?im)^\s*(?:#|--|//|/\*|\*|'|REM\b)?\s*(?:objective|business\s+objective|unit|owner|source\s+system|reporting\s+source|used\s+in|input|inputs)\s*:",
            text or "",
        )
    )


def _has_executable_calculation(text: str) -> bool:
    source = _strip_string_literals(text or "")
    return bool(
        re.search(r"(?im)\breturn\b[^\n;]*[+\-*/][^\n;]*", source)
        or re.search(r"(?is)\bselect\b.+[+\-*/].+\bas\b", source)
        or re.search(r"(?im)\b(?:SUM|AVG|COUNT|MIN|MAX|NULLIF)\s*\(", source)
        or re.search(r"(?im)\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*[^#\n;]*[+\-*/][^#\n;]*", source)
    )


def _has_return_arithmetic_calculation(text: str) -> bool:
    source = _strip_string_literals(text or "")
    return bool(re.search(r"(?im)\breturn\b[^\n;]*[+\-*/][^\n;]*", source))


def _strip_string_literals(text: str) -> str:
    source = text or ""
    source = re.sub(r'"""(?:.|\n)*?"""', '""', source)
    source = re.sub(r"'''(?:.|\n)*?'''", "''", source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', '""', source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", "''", source)
    return source


def _has_bad_formula_artifact(text: str) -> bool:
    source = text or ""
    return bool(
        re.search(r"(?i)\bN/A\b", source)
        or re.search(r"\b[A-Za-z]+/[A-Za-z_]+(?:/[A-Za-z_]+)?\b", source)
        or re.search(r"\b[0-9a-f]{24,}\b", source)
    )


def _candidate_review_record(candidate: Dict, reason: str, recommendation: str, file_path: str) -> Dict:
    context = candidate.get("code_context") or ""
    excerpt = "\n".join(context.splitlines()[:16])
    return {
        "candidate_name": candidate.get("name") or "Unnamed candidate",
        "detection_kind": candidate.get("_kind") or candidate.get("detection_kind") or "unspecified",
        "confidence": candidate.get("confidence"),
        "language": candidate.get("language"),
        "file_path": file_path,
        "file_line": candidate.get("file_line") or 1,
        "reason": reason,
        "recommendation": recommendation,
        "code_context_excerpt": excerpt,
    }


def evaluate_candidate_promotion(
    candidate: Dict,
    full_text: str,
    file_path: str,
    scan_root: str | None = None,
) -> Tuple[bool, Dict]:
    name = candidate.get("name") or ""
    kind = candidate.get("_kind") or candidate.get("detection_kind") or ""
    context = candidate.get("code_context") or ""
    combined = "\n".join([name, kind, context, os.path.basename(file_path or ""), full_text[:4000]])
    ext = os.path.splitext(file_path or "")[1].lower()
    normalized_path = os.path.normpath(file_path or "")
    normalized_root = os.path.normpath(scan_root or "")
    is_scenario_fixture = (
        "generated_scenario_kpis" in normalized_path.split(os.sep)
        or bool(re.search(r"(?im)^\s*#\s*Expected LEAP Result\s*:", context))
    )
    scanning_scenario_suite = normalized_root.endswith(
        os.path.join("data", "validation", "generated_scenario_kpis")
    )

    if is_scenario_fixture and not scanning_scenario_suite:
        return False, _candidate_review_record(
            candidate,
            "Scenario fixture evidence is not promoted during a whole-repository scan.",
            "Scan data/validation/generated_scenario_kpis directly when validating fixture scenarios.",
            file_path,
        )

    # 1. Reject clearly invalid, artificial, or non-business names
    invalid_name_patterns = [
        r"(?i)intentionalgoverror",
        r"(?i)data validation",
        r"(?i)test",
        r"(?i)mock",
        r"(?i)debug",
        r"(?i)\bsplit\s+ratio\b",
        r"(?i)\bnormalize\s+kpi\s+name\b",
    ]
    if any(re.search(p, name) for p in invalid_name_patterns):
        return False, _candidate_review_record(
            candidate,
            "Candidate name contains test/mock/debug wording rather than business KPI evidence.",
            "Keep as test artifact or add a clean explicit KPI declaration if this is intentional.",
            file_path,
        )
        
    # Must have a reasonable name length/content (not just 'KPI' or empty)
    if not name or len(name) < 3 or name.lower() == "kpi":
        return False, _candidate_review_record(
            candidate,
            "Candidate name is empty, too short, or generic.",
            "Add an explicit business KPI name near the implementation.",
            file_path,
        )

    if "\n" in name or re.search(r"(?i)\b(def|return|select|pass|assert|from|import)\b", name):
        return False, _candidate_review_record(
            candidate,
            "Candidate name appears to include executable code rather than a clean KPI label.",
            "Fix the source annotation so the KPI name is a single business label.",
            file_path,
        )

    if len(name) > 120 or re.search(r"[{};]", name):
        return False, _candidate_review_record(
            candidate,
            "Candidate name is too long or contains code delimiters.",
            "Use a concise business KPI label.",
            file_path,
        )

    # Explicit KPI annotations are authoritative, but still avoid obvious test/mock wrappers.
    has_explicit_kpi_marker = bool(
        re.search(r"(?im)(?:#|--|//|/\*|\*)\s*KPI(?:\d+)?\s*:", context)
        or re.search(r"(?im)^\s*KPI(?:\d+)?\s*:", context)
        or kind in {"comment", "sql_comment", "dax_measure", "csharp_attribute", "iec_block"}
    )
    has_formula_marker = _has_explicit_formula_marker(context)
    has_business_metadata = _has_explicit_business_metadata(context)
    has_executable_calc = _has_executable_calculation(context)

    blacklisted = bool(STRICT_FUNCTION_BLACKLIST.search(name))
    if blacklisted and not has_explicit_kpi_marker:
        return False, _candidate_review_record(
            candidate,
            "Candidate name matches helper/test/configuration wording and lacks explicit KPI evidence.",
            "Leave quarantined unless the source owner adds a KPI declaration and formula.",
            file_path,
        )

    weak_inferred_kinds = {
        "logic_fallback",
        "forced_fallback",
        "empty_file_fallback",
        "plsql_return_fallback",
    }
    medium_inferred_kinds = {
        "python_function",
        "method_name",
        "select_alias",
        "create_function",
        "create_view",
        "plsql_function",
        "hana_json",
        "dax_simple",
        "abap_report",
    }

    if kind in weak_inferred_kinds:
        return False, _candidate_review_record(
            candidate,
            "Weak fallback extraction detected math-like text but not enough business KPI evidence.",
            "Add explicit KPI and Formula comments if this should become a governed KPI dossier.",
            file_path,
        )

    if ext == ".csv":
        if has_explicit_kpi_marker and has_formula_marker and not _has_bad_formula_artifact(context):
            return True, {}
        return False, _candidate_review_record(
            candidate,
            "CSV candidate lacks explicit KPI and Formula evidence or contains register/log-style artifacts.",
            "Keep in Extraction Review unless the CSV is intentionally structured as a KPI evidence file.",
            file_path,
        )

    if has_explicit_kpi_marker:
        if has_formula_marker or has_executable_calc or has_business_metadata:
            return True, {}
        return False, _candidate_review_record(
            candidate,
            "Explicit KPI marker found, but no formula, executable calculation, or business metadata was found nearby.",
            "Add Formula, Objective, Unit, Owner, or executable calculation evidence.",
            file_path,
        )

    has_business_context = (
        _has_business_marker(name)
        or _has_business_marker(os.path.basename(file_path or ""))
        or _has_business_marker(context)
    )
    has_calculation_structure = _has_formula_with_business_shape(context)
    has_explicit_metric_language = bool(
        re.search(
            r"(?i)\b(formula|metric|performance indicator|business rule|calculation|measure)\b",
            "\n".join([name, kind, context, os.path.basename(file_path or "")]),
        )
    )

    if kind in medium_inferred_kinds:
        if kind in {"python_function", "method_name"} and not _has_return_arithmetic_calculation(context):
            return False, _candidate_review_record(
                candidate,
                "Inferred Python symbol does not return a local arithmetic KPI calculation.",
                "Add explicit KPI/Formula metadata or keep this helper function out of governed KPI dossiers.",
                file_path,
            )
        if has_business_context and has_calculation_structure and has_executable_calc:
            return True, {}
        return False, _candidate_review_record(
            candidate,
            "Inferred candidate did not combine business naming with local executable calculation evidence.",
            "Add explicit KPI/Formula metadata or move this to a governed KPI source artifact.",
            file_path,
        )

    if has_business_context and has_calculation_structure:
        return True, {}

    if has_explicit_metric_language and has_calculation_structure:
        return True, {}

    return False, _candidate_review_record(
        candidate,
        "Candidate did not meet the KPI promotion gate.",
        "Review manually; promote only after source evidence declares a business KPI and calculation path.",
        file_path,
    )


def _is_valid_kpi_candidate(candidate: Dict, full_text: str, file_path: str) -> bool:
    promoted, _review = evaluate_candidate_promotion(candidate, full_text, file_path)
    return promoted


def _extract_by_comment_tag(
    lines: List[str], pattern: re.Pattern, language: str
) -> List[Dict]:
    """Capture `KPI: Name` markers using a language-specific comment pattern."""
    out = []
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if not m:
            continue
        name = _normalize_name(m.group("name"))
        out.append(
            {
                "name": name,
                "language": language,
                "file_line": i + 1,
                "code_context": _window(lines, i),
                "_rank": 5,  # explicit KPI comments are stronger than inferred names
                "_kind": "comment",
            }
        )
    return out


def _extract_python(text: str) -> List[Dict]:
    lines = text.splitlines()
    out: List[Dict] = []

    # # KPI: Name or # KPI001: Name
    out += _extract_by_comment_tag(
        lines, re.compile(r"#\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "python"
    )

    # Functions with KPI-ish names
    for i, line in enumerate(lines):
        m = re.search(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
        if not m:
            continue
        fn = m.group(1)
        if any(
            k in fn.lower()
            for k in (
                "kpi",
                "yield",
                "percentage",
                "ratio",
                "throughput",
                "oee",
                "variance",
                "recovery",
                "cost",
                "emission",
            )
        ):
            out.append(
                {
                    "name": _normalize_name(fn.replace("_", " ")),
                    "language": "python",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 2,  # add rank for function name
                    "_kind": "python_function",
                }
            )
    return out


def _extract_csharp_vb(text: str, language: str) -> List[Dict]:
    lines = text.splitlines()
    out: List[Dict] = []

    # C# attribute form: [KPI("Name")]
    for i, line in enumerate(lines):
        m = re.search(
            r"\[\s*KPI(?:Attribute)?\s*\(\s*\"(?P<name>[^\"]+)\"\s*\)\s*\]", line, re.I
        )
        if m:
            out.append(
                {
                    "name": _normalize_name(m.group("name")),
                    "language": language,
                    "file_line": i + 1,
                    "code_context": _window(
                        lines, i, 5, 60
                    ),  # widened after-context for Return
                    "_rank": 3,
                    "_kind": "csharp_attribute",
                }
            )

    # C#: // KPI: Name or // KPI001: Name
    out += _extract_by_comment_tag(
        lines, re.compile(r"//\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), language
    )
    # VB.NET: ' KPI: Name or ' KPI001: Name
    out += _extract_by_comment_tag(
        lines, re.compile(r"'\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), language
    )

    # Methods like CalculateXxxKpi(...)
    for i, line in enumerate(lines):
        m = re.search(r"\b(Calculate|Compute)[A-Za-z0-9_]*Kpi\s*\(", line, re.I)
        if m:
            name = _normalize_name(m.group(0).split("(")[0])
            out.append(
                {
                    "name": name,
                    "language": language,
                    "file_line": i + 1,
                    "code_context": _window(lines, i, 5, 60),
                    "_rank": 2,
                    "_kind": "method_name",
                }
            )
    return out


def _extract_sql_like(text: str, dialect: str) -> List[Dict]:
    lines = text.splitlines()
    out: List[Dict] = []

    # Normalize potential BOM and EOL noise
    stripped_lines = [ln.lstrip("\ufeff").rstrip("\r\n") for ln in lines]

    # 1) Prefer explicit KPI lines:
    comments = []
    # Match "-- KPI: ...", "-- KPI001: ...", or "// KPI001: ..."
    for i, line in enumerate(stripped_lines):
        m = re.search(
            r"^\s*(?:--|//)\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", line, re.I
        )
        if m:
            comments.append((i, _normalize_name(m.group("name"))))
    # Match "/* KPI: ... */" or "/* KPI001: ... */" (inline)
    for i, line in enumerate(stripped_lines):
        m = re.search(r"/\*\s*KPI(?:\d+)?\s*:\s*(?P<name>[^*]+)\*/", line, re.I)
        if m:
            comments.append((i, _normalize_name(m.group("name"))))
    # NEW: also match bare "KPI: ..." or "KPI001: ..." even if not in a comment (safety net)
    if not comments:
        for i, line in enumerate(stripped_lines):
            m = re.search(r"\bKPI(?:\d+)?\s*:\s*(?P<name>.+)$", line, re.I)
            if m:
                comments.append((i, _normalize_name(m.group("name"))))
                break

    for i, name in comments:
        if dialect.lower() == "plsql":
            code_context = _window(lines, i, before=0, after=160)
        else:
            code_context = _expand_forward_statement(lines, i)
        out.append(
            {
                "name": name,
                "language": dialect,
                "file_line": i + 1,
                "code_context": code_context,
                "_rank": 3,
                "_kind": "sql_comment",
            }
        )

    has_comment = len(comments) > 0

    # 2) Fallbacks if no comment matched:
    if not has_comment:
        # 2a) CREATE FUNCTION <any_name> (be tolerant; not only kpi_*)
        for i, line in enumerate(stripped_lines):
            m = re.search(
                r"\bcreate\s+(?:or\s+replace\s+)?function\s+(?P<fn>[A-Za-z0-9_\.$]+)",
                line,
                re.I,
            )
            if m:
                fn_name = _normalize_name(m.group("fn"))
                out.append(
                    {
                        "name": fn_name,
                        "language": dialect,
                        "file_line": i + 1,
                        "code_context": _expand_forward_statement(lines, i),
                        "_rank": 2,
                        "_kind": "create_function",
                    }
                )
                # Keep scanning; multiple functions are possible

        # 2b) CREATE VIEW view_kpi_* AS ...
        for i, line in enumerate(stripped_lines):
            m = re.search(
                r"\bcreate\s+view\s+([A-Za-z0-9_\.]*kpi[A-Za-z0-9_\.]*)\b", line, re.I
            )
            if m:
                out.append(
                    {
                        "name": _normalize_name(m.group(1)),
                        "language": dialect,
                        "file_line": i + 1,
                        "code_context": _window(lines, i, 5, 120),
                        "_rank": 2,
                        "_kind": "create_view",
                    }
                )

        # 2c) SELECT ... expr AS alias. Accept explicit KPI/measure aliases and
        # common enterprise metric suffixes used in committee/demo suites.
        for i, line in enumerate(stripped_lines):
            m = re.search(
                r"\bas\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\b", line, re.I
            )
            if m and re.search(
                r"(?i)(?:^kpi_|^measure_|_kpi$|_pct$|_percent$|_percentage$|_ratio$|_rate$|_yield$|_intensity$|_score$|_variance$|_cost$|_leakage$)",
                m.group("alias"),
            ):
                out.append(
                    {
                        "name": _normalize_name(m.group("alias")),
                        "language": dialect,
                        "file_line": i + 1,
                        "code_context": _window(lines, i, 3, 80),
                        "_rank": 2,
                        "_kind": "select_alias",
                    }
                )

        # 2d) LAST-RESORT (PL/SQL only): if we see a math RETURN, emit one KPI using the file name
        if dialect.lower() in {"plsql"} and not out:
            # Look for a mathy RETURN in the whole text
            if re.search(r"(?is)\breturn\b.+[*/+-].+", text):
                base_name = "PLSQL KPI"
                # Derive a human-ish name from the file if available
                try:
                    import os as _os

                    base_name = (
                        _normalize_name(
                            _os.path.splitext(
                                _os.path.basename(__file__ if False else "")
                            )[0]
                        )
                        or "PLSQL KPI"
                    )
                except Exception:
                    pass
                # Use a wide context: the whole file, so formula extractor can grab the RETURN expression
                out.append(
                    {
                        "name": base_name,
                        "language": dialect,
                        "file_line": 1,
                        "code_context": text,
                        "_rank": 1,
                        "_kind": "plsql_return_fallback",
                    }
                )

    return out


def _extract_hana(text: str) -> List[Dict]:
    """
    SAP HANA SQLScript artifacts often embed SQLScript with comments like -- or /* ... */.
    Handle both SQL-like content and JSON-style .hdbview definitions.
    """
    # 1) Try SQL-like first
    out = _extract_sql_like(text, "hana")
    if out:
        return out

    # 2) JSON-style .hdbview fallback
    try:
        import json

        obj = json.loads(text)
        vd = obj.get("viewDefinition") or {}
        cols = vd.get("columns") or []
        best = None
        for c in cols:
            name = (c.get("name") or "").strip()
            expr = (c.get("expression") or "").strip()
            if not name or not expr:
                continue
            score = 1
            if "kpi" in name.lower():
                score += 2
            if any(ch in expr for ch in "*/+-"):
                score += 1
            best = max(
                [best, (score, name, expr)] if best else [(score, name, expr)],
                key=lambda t: t[0],
            )
        if best:
            _, name, expr = best
            code = f"SELECT {expr} AS {name}"
            return [
                {
                    "name": _normalize_name(name),
                    "language": "hana",
                    "file_line": 1,
                    "code_context": code,
                    "_rank": 2,
                    "_kind": "hana_json",
                }
            ]
    except Exception:
        pass

    return []


def _extract_tsql(text: str) -> List[Dict]:
    """T‑SQL specific files (.tsql) → reuse SQL-like extraction with label 'tsql'."""
    return _extract_sql_like(text, "tsql")


def _extract_plsql(text: str) -> List[Dict]:
    """PL/SQL files (.pks/.pkb/.pls) → reuse SQL-like extraction with label 'plsql'."""
    out = _extract_sql_like(text, "plsql")
    if out:
        return out
    # Fallback for .pks package spec: capture FUNCTION signatures
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"\bFUNCTION\s+([A-Za-z0-9_\.$]+)", line, re.I)
        if m:
            fn = _normalize_name(m.group(1))
            return [
                {
                    "name": fn,
                    "language": "plsql",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 2,
                    "_kind": "plsql_function",
                }
            ]
    return out


def _extract_dax(text: str) -> List[Dict]:
    """Power BI DAX code."""
    lines = text.splitlines()
    out: List[Dict] = []
    seen_names = set()

    # DEFINE MEASURE 'Table'[Measure] = ...
    for i, line in enumerate(lines):
        m = re.search(
            r"\bDEFINE\s+MEASURE\s+[^\[]*\[(?P<name>[^\]]+)\]\s*=", line, re.I
        )
        if m:
            name = _normalize_name(m.group("name"))
            seen_names.add(name.lower())
            out.append(
                {
                    "name": name,
                    "language": "dax",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 3,
                    "_kind": "dax_measure",
                }
            )

    # Simple measure lines: Name = Expression
    for i, line in enumerate(lines):
        if re.match(r"\s*(VAR|RETURN|EVALUATE)\b", line, re.I):
            continue
        m = re.search(r"(?P<name>[A-Za-z0-9 _\[\]\.]+?)\s*=\s*.+", line)
        if m:
            name = _normalize_name(m.group("name"))
            if name.lower() not in seen_names and len(name.strip()) > 2:
                seen_names.add(name.lower())
                out.append(
                    {
                        "name": name,
                        "language": "dax",
                        "file_line": i + 1,
                        "code_context": _window(lines, i),
                        "_rank": 2,
                        "_kind": "dax_simple",
                    }
                )

    # -- KPI: Name (only add if not already captured as a measure)
    for i, line in enumerate(lines):
        m = re.search(r"--\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", line, re.I)
        if m:
            name = _normalize_name(m.group("name"))
            if name.lower() not in seen_names:
                out.append(
                    {
                        "name": name,
                        "language": "dax",
                        "file_line": i + 1,
                        "code_context": _window(lines, i),
                        "_rank": 3,
                        "_kind": "dax_comment",
                    }
                )
    return out


def _extract_abap(text: str) -> List[Dict]:
    lines = text.splitlines()
    out: List[Dict] = []

    # "* KPI: Name" or "* KPI001: Name"
    out += _extract_by_comment_tag(
        lines, re.compile(r"\*\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "abap"
    )

    # REPORT ... KPI ...
    for i, line in enumerate(lines):
        if re.search(r"\bREPORT\b.*\bKPI\b", line, re.I):
            out.append(
                {
                    "name": _normalize_name(line),
                    "language": "abap",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 2,
                    "_kind": "abap_report",
                }
            )
    return out


def _extract_iec_st(text: str) -> List[Dict]:
    """
    IEC 61131‑3 Structured Text and PLC textual code.
    Comment styles: // line comment, (* block comment *), and sometimes {**}.
    We rely primarily on explicit 'KPI:' tags in comments.
    """
    lines = text.splitlines()
    out: List[Dict] = []

    # // KPI: Name or // KPI001: Name
    out += _extract_by_comment_tag(
        lines, re.compile(r"//\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "iec_st"
    )

    # (* KPI: Name *) or (* KPI001: Name *)
    for i, line in enumerate(lines):
        m = re.search(r"\(\*\s*KPI(?:\d+)?\s*:\s*(?P<name>[^*]+)\*\)", line, re.I)
        if m:
            out.append(
                {
                    "name": _normalize_name(m.group("name")),
                    "language": "iec_st",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 3,
                    "_kind": "iec_block",
                }
            )

    # {** KPI: Name **} or {** KPI001: Name **}
    for i, line in enumerate(lines):
        m = re.search(r"\{\*+\s*KPI(?:\d+)?\s*:\s*(?P<name>[^*]+)\*+\}", line, re.I)
        if m:
            out.append(
                {
                    "name": _normalize_name(m.group("name")),
                    "language": "iec_st",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 3,
                    "_kind": "iec_brace",
                }
            )

    return out



def _extract_logic_heuristics(text: str) -> List[Dict]:
    out = []
    lines = text.splitlines()
    # Detect patterns like: yield_pct = (...) / (...)
    # Or return (a+b) / c
    # This is a fallback, so confidence will be low.
    pattern = re.compile(r'(?i)(?:[a-z_][a-z0-9_]*\s*[:=]\s*|return\s+)(?P<expr>[^;\n]+[\+\-\*/][^;\n]+)')
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if m:
            expr = m.group('expr').strip()
            out.append({
                'name': 'Inferred Logic KPI',
                'language': 'generic',
                'file_line': i + 1,
                'code_context': 'Inferred logic: ' + expr,
                '_rank': 0,
                '_kind': 'logic_fallback',
            })
    return out

def _extract_generic(text: str) -> List[Dict]:
    """Fallback extractor for miscellaneous text files."""
    lines = text.splitlines()
    out: List[Dict] = []
    # Support common comment styles in mixed text
    out += _extract_by_comment_tag(
        lines, re.compile(r"#\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "generic"
    )
    out += _extract_by_comment_tag(
        lines, re.compile(r"//\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "generic"
    )
    out += _extract_by_comment_tag(
        lines, re.compile(r"--\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "generic"
    )
    out += _extract_by_comment_tag(
        lines, re.compile(r"^\s*\*\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I), "generic"
    )  # ABAP-style
    # Also allow bare lines: "KPI: ..." or "KPI001: ..." with no comment marker
    bare_pat = re.compile(r"^\s*KPI(?:\d+)?\s*:\s*(?P<name>.+)$", re.I)
    for i, line in enumerate(lines):
        # C/SQL block comments
        m = re.search(r"/\*\s*KPI(?:\d+)?\s*:\s*(?P<name>[^*]+)\*/", line, re.I)
        if m:
            out.append(
                {
                    "name": _normalize_name(m.group("name")),
                    "language": "generic",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 3,
                    "_kind": "generic_block",
                }
            )
            continue
        # IEC ST block comments: (* KPI: ... *)
        m_st = re.search(r"\(\*\s*KPI(?:\d+)?\s*:\s*(?P<name>[^*]+)\*\)", line, re.I)
        if m_st:
            out.append(
                {
                    "name": _normalize_name(m_st.group("name")),
                    "language": "generic",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 3,
                    "_kind": "generic_iec",
                }
            )
            continue
        mb = bare_pat.search(line)
        if mb:
            out.append(
                {
                    "name": _normalize_name(mb.group("name")),
                    "language": "generic",
                    "file_line": i + 1,
                    "code_context": _window(lines, i),
                    "_rank": 2,
                    "_kind": "generic_bare",
                }
            )
    return out


# ---------- Dispatcher ----------


def _detect_language_by_extension(path_lower: str) -> str:
    """Map file extension to a language."""
    for ext, lang in _SUPPORTED_EXTS.items():
        if path_lower.endswith(ext):
            return lang
    return "generic"


def _extract_from_text(text: str, language_hint: str) -> List[Dict]:
    lang = language_hint
    if lang == "python":
        return _extract_python(text)
    if lang in ("csharp", "vbnet"):
        return _extract_csharp_vb(text, lang)
    if lang in ("sql",):
        return _extract_sql_like(text, "sql")
    if lang == "tsql":
        return _extract_tsql(text)
    if lang == "plsql":
        return _extract_plsql(text)
    if lang == "hana":
        return _extract_hana(text)
    if lang == "dax":
        return _extract_dax(text)
    if lang == "abap":
        return _extract_abap(text)
    if lang == "iec_st":
        return _extract_iec_st(text)
    return _extract_generic(text)


# ---------- Public API ----------


def find_kpis_in_directory(root_path: str, include_stats: bool = False):
    """
    Walk a directory tree and extract KPI candidates across multiple languages.

    Returns:
        List[Dict] by default. If include_stats=True, returns (kpis, stats).
    """
    results: List[Dict] = []
    seen_kpi_names = set()
    stats = _empty_scan_stats()

    def done():
        return (results, stats) if include_stats else results

    if not root_path:
        return done()

    try:
        base = os.path.expanduser(root_path)
        if not os.path.isabs(base):
            base = os.path.abspath(base)
        if not os.path.isdir(base):
            return done()
    except Exception:
        return done()

    stats.update(_count_filesystem_inventory(base))

    for dirpath, dirnames, filenames in os.walk(base):
        # prune directories in-place
        before_dirs = list(dirnames)
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_ignored_dir_name(d)
        ]
        stats["ignored_dirs"] += len(before_dirs) - len(dirnames)
        stats["files_after_directory_exclusions"] += len(filenames)

        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            path = os.path.join(dirpath, fn)

            if fn in IGNORE_FILES or fn.startswith("."):
                stats["ignored_files"] += 1
                continue

            # --- Skip image and binary files entirely ---
            if ext in IGNORE_EXTS:
                stats["skipped_binary_files"] += 1
                continue

            # Extension filter. Set KPI_SCAN_ALL=1 only when deliberately testing
            # unknown text-like extensions; by default, avoid project/build noise.
            _scan_all_env = os.environ.get("KPI_SCAN_ALL")
            scan_all = (
                False
                if _scan_all_env is None
                else (_scan_all_env in {"1", "true", "True"})
            )
            if ALLOWED_EXTS and (ext not in ALLOWED_EXTS) and not scan_all:
                stats["unsupported_files"] += 1
                continue

            stats["files_scanned"] += 1

            # Count analyzed source/data lines only after extension filtering.
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    stats["lines_analyzed"] += sum(1 for _ in f)
            except Exception:
                pass

            # size filter
            try:
                if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
                    stats["oversized_files"] += 1
                    continue
            except OSError:
                continue

            # Detect language
            p_lower = path.lower()
            lang = _detect_language_by_extension(p_lower)

            # Read file safely
            text = _read_text_file_safe(path)
            if not text:
                stats["empty_or_unreadable_files"] += 1
                continue
            else:
                # Extract KPIs for this file; if extension was not allowed but KPI_SCAN_ALL is on,
                # still attempt generic extraction as a fallback
                try:
                    if (ALLOWED_EXTS and ext not in ALLOWED_EXTS) and scan_all:
                        file_kpis = _extract_generic(text) or []
                    else:
                        file_kpis = _extract_from_text(text, lang) or []
                        # Fallback: if language-specific extractor finds nothing, try generic patterns
                        if not file_kpis:
                            file_kpis = _extract_generic(text) or []
                except Exception:
                    file_kpis = []

                # Attach file path and accumulate
                for k in file_kpis:
                    k["file_path"] = path
                    # Try to extract an explicit formula from comments if helper available
                    if _extract_formula_from_comments:
                        try:
                            formula = _extract_formula_from_comments(text.splitlines())
                            if formula:
                                k["formula"] = formula
                        except Exception:
                            pass

                if not file_kpis:
                    # Logic-based fallback: if no KPIs were found, scan the text for
                    # explicit mathematical expressions or return statements.
                    try:
                        # Detect mathematical patterns: division, arithmetic, or return expressions
                        math_patterns = [
                            r'[\w\s]+\s*[:=]\s*.*[\+\-\*/].*',      # Assignment with arithmetic
                            r'return\s+.*[\+\-\*/].*',             # Return with arithmetic
                            r'SELECT\s+.*[\+\-\*/].*[\s\w]*FROM',   # SQL computed column
                            r'(\w+)\s*/\s*(\w+)'                    # Division/Ratio
                        ]
                        has_logic = any(re.search(p, text, re.I | re.S) for p in math_patterns)
                        
                        if has_logic:
                            base_name = os.path.basename(path)
                            name_stem = os.path.splitext(base_name)[0]
                            synth_name = _normalize_name(name_stem)
                            ctx = text
                            if len(ctx) > 8000:
                                ctx = ctx[:4000] + "\n...\n" + ctx[-4000:]
                            file_kpis = [
                                {
                                    "name": synth_name or "KPI",
                                    "language": lang,
                                    "file_line": 1,
                                    "code_context": ctx,
                                    "_rank": 0,
                                    "_kind": "logic_fallback",
                                }
                            ]
                    except Exception:
                        pass
                    if not file_kpis:
                        # Optional compatibility mode for synthetic demo sets where
                        # every source file should become a page. Disabled by default
                        # because it turns ordinary project files into false KPIs.
                        if os.environ.get("KPI_FORCE_FILE_FALLBACK") in {
                            "1",
                            "true",
                            "True",
                        }:
                            try:
                                base_name = os.path.basename(path)
                                name_stem = os.path.splitext(base_name)[0]
                                synth_name = _normalize_name(name_stem)
                                ctx = text
                                if len(ctx) > 8000:
                                    ctx = ctx[:4000] + "\n...\n" + ctx[-4000:]
                                file_kpis = [
                                    {
                                        "name": synth_name or "KPI",
                                        "language": lang,
                                        "file_line": 1,
                                        "code_context": ctx,
                                        "_rank": -1,
                                        "_kind": "forced_fallback",
                                    }
                                ]
                            except Exception:
                                pass
                        if not file_kpis:
                            continue

            for k in file_kpis:
                k["file_path"] = k.get("file_path") or path
                try:
                    file_line = int(k.get("file_line") or 1)
                except (TypeError, ValueError):
                    file_line = 1
                k["file_line"] = max(1, file_line)
            # Promotion gate: keep strong KPI evidence for dossiers and route
            # weak KPI-like candidates to Extraction Review instead of silently
            # generating executive dossiers from helper code, logs, or registers.
            before_filter_count = len(file_kpis)
            promoted_kpis = []
            for k in file_kpis:
                promoted, review_record = evaluate_candidate_promotion(k, text, path, base)
                if promoted:
                    promoted_kpis.append(k)
                elif review_record:
                    stats["candidate_review"].append(review_record)
            file_kpis = promoted_kpis

            # Deduplicate by name
            seen_names = set()
            deduplicated_kpis = []
            for k in file_kpis:
                n = k.get("name") or "Unknown"
                if n not in seen_names:
                    seen_names.add(n)
                    deduplicated_kpis.append(k)
            file_kpis = deduplicated_kpis

            stats["filtered_non_kpi_candidates"] += before_filter_count - len(file_kpis)
            if not file_kpis:
                continue

            # Pick a single best KPI per file
            def rank(item: Dict) -> Tuple[int, int]:
                r = int(item.get("_rank", 0))
                n = item.get("name") or ""
                human = (
                    1 if re.search(r"[ ()\[\]]", n) else 0
                )  # prefer names with spaces/paren/brackets
                return (r, human)

            best = max(file_kpis, key=rank)

            # Compute confidence based on rank and kind
            def compute_confidence(item: Dict) -> int:
                r = int(item.get("_rank", 0))
                kind = item.get("_kind", "")
                base = {3: 95, 2: 85, 1: 75, 0: 60, -1: 50}
                conf = base.get(r, 70)
                # Boost for explicit comment tags
                if kind in (
                    "comment",
                    "sql_comment",
                    "dax_measure",
                    "csharp_attribute",
                    "iec_block",
                ):
                    conf = max(conf, 90)
                # Penalize fallbacks
                if kind in ("empty_file_fallback", "forced_fallback"):
                    conf = min(conf, 55)
                return conf

            best["confidence"] = compute_confidence(best)
            best["detection_kind"] = best.get("_kind", "unspecified")

            # Strip internal helper fields
            best.pop("_rank", None)
            best.pop("_kind", None)

            if best.get("name") not in seen_kpi_names:
                results.append(best)
                seen_kpi_names.add(best.get("name"))

    return done()
