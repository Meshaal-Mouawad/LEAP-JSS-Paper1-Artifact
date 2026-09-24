import os
import hashlib
import json
import jinja2
import re
import shutil
import time
import subprocess
from pathlib import Path
from urllib.parse import quote, urlencode
from .kpi_extractor import find_kpis_in_directory
from .ai_generator import _ai_engine_enabled, generate_kpi_details
from .governance import attach_governance
from .paths import BUSINESS_OVERRIDES_PATH, KNOWLEDGE_BASE_DIR

# Public API from this module
__all__ = ["generate_bluebook"]


def _worker_context(ai_enabled: bool, max_workers: int) -> str:
    """Expose worker count only when optional AI enrichment is active."""
    if not ai_enabled:
        return ""
    return f" with {max_workers} AI enrichment workers"

ROOT_DIR = Path(__file__).parent.parent
DOCS_SOURCE_DIR = ROOT_DIR / "docs"
TEMPLATE_DIR = ROOT_DIR / "templates"
UNMAPPED_DEVELOPER_LINEAGE = (
    "UNMAPPED: Utility logic detected without explicit database schema lineage."
)
DEFINITION_OVERRIDE_FIELDS = {
    "description",
    "objective",
    "formula_description",
    "used_in_kpis",
    "input_measure",
    "unit_of_measure",
    "reporting_source",
    "comments",
}
PROFESSIONAL_UNCERTAINTY_TEXT = {
    "objective": "Business objective is not declared in the source evidence. Owner confirmation is required before executive use.",
    "formula": "Certified formula statement not declared in implementation comments. LEAP presents the executable calculation evidence for owner confirmation.",
    "usage": "Business-process usage mapping is not declared in the source evidence.",
    "inputs": "Explicit input-field list is not declared in the source evidence.",
    "unit": "Unit of measure is not declared in the source evidence.",
    "lineage": "No upstream system mapping was identified in the implementation evidence.",
    "comments": "Compliance mode preserved only implementation-grounded evidence; unresolved business context is routed to owner confirmation.",
}
DISPLAY_NAME_OVERRIDES = {
    "kpi flare recovery pct": "Flare Recovery Percentage (%)",
    "oee %": "Overall Equipment Effectiveness (OEE)",
    "oee": "Overall Equipment Effectiveness (OEE)",
}


def _package_display_path(value: str | Path) -> str:
    """Return a portable repository-relative path for generated materials."""
    try:
        return str(Path(value).expanduser().resolve().relative_to(ROOT_DIR))
    except (OSError, ValueError):
        return Path(value).name


def _business_display_name(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return "Enterprise KPI"
    override = DISPLAY_NAME_OVERRIDES.get(name.lower())
    if not override:
        normalized_key = re.sub(r"[_\-]+", " ", name.lower())
        normalized_key = re.sub(r"\s+", " ", normalized_key).strip()
        override = DISPLAY_NAME_OVERRIDES.get(normalized_key)
    if override:
        return override
    cleaned = re.sub(r"\bkpi\b", "", name, flags=re.I)
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(r"\bpct\b", "%", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = name
    if cleaned.islower() or "_" in name or "-" in name:
        words = []
        for part in cleaned.split(" "):
            if part in {"%", "$"} or re.search(r"\([^)]+\)", part):
                words.append(part)
            elif part.upper() in {"SOX", "NOX", "OEE", "MTBF", "MFI"}:
                words.append(part.upper())
            else:
                words.append(part.capitalize())
        cleaned = " ".join(words)
    cleaned = cleaned.replace("Sox", "SOx")
    cleaned = cleaned.replace("Mfi", "MFI")
    cleaned = cleaned.replace("Mtbf", "MTBF")
    cleaned = cleaned.replace("On-spec", "On-Spec")
    cleaned = cleaned.replace("Delta-t", "Delta-T")
    if cleaned.endswith(" %"):
        cleaned = cleaned[:-2] + " (%)"
    return cleaned


def _business_label(value: str) -> str:
    """Format generated business labels without degrading enterprise acronyms."""
    label = str(value or "").replace("_", " ").strip()
    if not label:
        return ""
    label = re.sub(r"\s+", " ", label).title()
    acronym_map = {
        "Abap": "ABAP",
        "Api": "API",
        "Csv": "CSV",
        "Dax": "DAX",
        "Ecc": "ECC",
        "Eu": "EU",
        "Gdpr": "GDPR",
        "Hana": "HANA",
        "Hse": "HSE",
        "Iso": "ISO",
        "Kpi": "KPI",
        "Mfi": "MFI",
        "Mtbf": "MTBF",
        "Nca": "NCA",
        "Oee": "OEE",
        "Pdpl": "PDPL",
        "Raci": "RACI",
        "Soc2": "SOC2",
        "Sox": "SOx",
    }
    for source, target in acronym_map.items():
        label = re.sub(rf"\b{re.escape(source)}\b", target, label)
    return label


def _prepare_kpi_display_names(kpis: list[dict]) -> None:
    for kpi in kpis:
        raw_name = str(kpi.get("name") or "").strip()
        display_name = _business_display_name(raw_name)
        kpi["raw_name"] = raw_name
        kpi["display_name"] = display_name
        kpi["name_was_normalized"] = bool(raw_name and display_name != raw_name)


def _executive_text(value: str, fallback_key: str) -> str:
    text = str(value or "").strip()
    upper = text.upper()
    if not text or "UNDETERMINED" in upper or "LINEAGE UNDETERMINED" in upper:
        return PROFESSIONAL_UNCERTAINTY_TEXT[fallback_key]
    return text


def _load_json_file(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return default
    return default


def _definition_override_candidates(kpi: dict) -> list[str]:
    candidates = [
        str(kpi.get("name") or "").strip(),
        str(kpi.get("function_name") or "").strip(),
        str(kpi.get("source_file_display") or "").strip(),
        Path(str(kpi.get("file_path") or "")).stem,
    ]
    return [c for c in candidates if c]


def _load_definition_overrides() -> dict:
    merged: dict = {}
    docs_overrides = _load_json_file(BUSINESS_OVERRIDES_PATH, {})
    if isinstance(docs_overrides, dict):
        for name, fields in docs_overrides.items():
            if isinstance(fields, dict):
                merged[name] = {
                    "status": "APPROVED_BY_BUSINESS",
                    "fields": fields,
                    "source": str(BUSINESS_OVERRIDES_PATH.relative_to(ROOT_DIR)),
                }
    for override_path in (KNOWLEDGE_BASE_DIR / "overrides.json",):
        kb_overrides = _load_json_file(override_path, {})
        kb_kpis = kb_overrides.get("kpis", {}) if isinstance(kb_overrides, dict) else {}
        if isinstance(kb_kpis, dict):
            for name, block in kb_kpis.items():
                if isinstance(block, dict):
                    fields = block.get("fields", {})
                    if isinstance(fields, dict):
                        merged[name] = {
                            "status": block.get("status") or "APPROVED_BY_BUSINESS",
                            "fields": fields,
                            "source": str(override_path.relative_to(ROOT_DIR)),
                            "file_signature": block.get("file_signature") or "",
                        }
    return merged


def _apply_definition_override(kpi: dict, details: dict, overrides: dict) -> dict:
    if not overrides:
        return details
    override = None
    for candidate in _definition_override_candidates(kpi):
        if candidate in overrides:
            override = overrides[candidate]
            break
    if not override:
        return details
    override_signature = str(override.get("file_signature") or "").strip()
    current_signature = str(kpi.get("source_file_signature") or "").strip()
    if override_signature and override_signature != current_signature:
        return details
    fields = override.get("fields", {}) if isinstance(override, dict) else {}
    if not isinstance(fields, dict):
        return details
    updated = dict(details or {})
    for key in DEFINITION_OVERRIDE_FIELDS:
        value = fields.get(key)
        if value is not None and str(value).strip():
            updated[key] = value
    updated["_override_status"] = override.get("status") or "APPROVED_BY_BUSINESS"
    updated["_override_source"] = override.get("source") or "manual override ledger"
    return updated


def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    s = text
    s = re.sub(r"(?is)<\s*(script|style)\b.*?>.*?<\s*/\s*\1\s*>", "", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


LATEX_COMMAND_NORMALIZATIONS = {
    "frac": "frac",
    "mathrm": "mathrm",
    "text": "text",
    "operatorname": "operatorname",
    "sum": "sum",
    "bar": "bar",
    "times": "times",
    "left": "left",
    "right": "right",
}


def _looks_like_latex_formula(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return bool(
        re.search(
            r"\\(?:frac|Frac|mathrm|Mathrm|text|Text|operatorname|Operatorname|sum|Sum|times|Times)\b",
            value,
        )
    )


def _normalize_latex_formula(value: str) -> str:
    """
    Preserve explicit source-provided LaTeX as MathJax input.

    LEAP also has a code-expression renderer that turns source expressions like
    `operatingHours / numberOfFailures` into LaTeX. Explicit formulas such as
    `\\mathrm{MTBF} = \\frac{...}{...}` must not go through that renderer:
    tokenization would treat LaTeX commands as business words and corrupt them
    into `\\Mathrm`, `\\Frac`, escaped braces, or `\\text{...}` blocks.
    """
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    latex = _sanitize_text(value)
    latex = latex.strip().strip("$")

    def normalize_command(match: re.Match) -> str:
        command = match.group(1)
        canonical = LATEX_COMMAND_NORMALIZATIONS.get(command.lower())
        return "\\" + (canonical or command)

    latex = re.sub(r"\\([A-Za-z]+)\b", normalize_command, latex)
    
    # Handle specific LaTeX escape sequences that represent business-label punctuation.
    # Keep these as readable label separators; raw underscores inside \mathrm{}
    # are invalid because MathJax treats "_" as subscript syntax.
    latex = re.sub(r"\\text\s*\{-\}", "-", latex)
    # Replace \% with nothing (remove percent from business labels)
    latex = re.sub(r"\\%", "", latex)
    
    # Normalize business labels inside \text{} blocks before conversion
    # This handles cases like \text{-} where hyphens need normalization
    def normalize_text_content(match: re.Match) -> str:
        content = match.group(1)
        # Apply business label normalization to the content
        content = _normalize_business_label_in_latex(content)
        return r"\text{" + content + "}"
    
    latex = re.sub(r"\\text\s*\{([^{}]+)\}", normalize_text_content, latex)
    
    # Now convert \text{} to \mathrm{} via _math_label
    latex = re.sub(
        r"\\text\s*\{([^{}]+)\}",
        lambda m: _math_label(m.group(1)),
        latex,
    )
    
    # Also normalize business labels inside existing \mathrm{} blocks
    # This handles cases where source already has \mathrm{} wrapping
    def normalize_mathrm_content(match: re.Match) -> str:
        content = match.group(1)
        # Remove nested \mathrm{} if present (from \text{} conversion)
        content = re.sub(r"\\mathrm\s*\{([^{}]+)\}", r"\1", content)
        # Apply business label normalization to the content
        content = _normalize_business_label_in_latex(content)
        return r"\mathrm{" + content.replace(" ", r"\,") + "}"
    
    latex = re.sub(r"\\mathrm\s*\{([^{}]+)\}", normalize_mathrm_content, latex)
    
    latex = re.sub(r"\s+", " ", latex).strip()
    return latex


def _normalize_business_identifier(name: str) -> str:
    """
    Normalize business identifiers (LHS of formulas) by removing presentation tokens
    while preserving business words.
    
    Rules:
    - Remove presentation tokens: (%), (kg), (tons/day), (P/E), etc.
    - Preserve business words: Percentage, Throughput, Ratio, Yield, etc.
    - Convert spaces to underscores
    - Convert hyphens to underscores
    - Collapse multiple underscores
    - Trim leading/trailing underscores
    """
    # Remove presentation tokens (units in parentheses)
    # Match patterns like (%), (kg), (tons/day), (P/E), (PE), etc.
    normalized = re.sub(r"\s*\([^)]*\)", "", name)
    
    # Remove trailing % without parentheses
    normalized = re.sub(r"\s*%\s*$", "", normalized)
    
    # Convert hyphens to underscores
    normalized = re.sub(r"([a-zA-Z0-9]+)-([a-zA-Z0-9]+)", r"\1_\2", normalized)
    normalized = re.sub(r"([a-zA-Z0-9]+)\s*-\s*([a-zA-Z0-9]+)", r"\1_\2", normalized)
    
    # Convert spaces to underscores
    normalized = re.sub(r"\s+", "_", normalized)
    
    # Collapse multiple underscores
    normalized = re.sub(r"_+", "_", normalized)
    
    # Trim leading/trailing underscores
    normalized = normalized.strip("_")
    
    return normalized


def _normalize_business_label_in_latex(content: str) -> str:
    r"""
    Normalize business labels inside LaTeX \mathrm{} blocks.
    Removes presentation-only units/markers while preserving readable business
    words. Do not emit raw underscores here: inside math mode, underscores are
    subscript operators and can invalidate MathJax.
    """
    normalized = str(content or "")
    normalized = normalized.replace(r"\,", " ").replace(r"\ ", " ")
    normalized = re.sub(r"\s*\([^)]*\)", "", normalized)
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"([a-zA-Z0-9]+)\s*-\s*([a-zA-Z0-9]+)", r"\1 \2", normalized)
    
    # Remove trailing % from business labels (but preserve scale factors like \times 100)
    # Only remove % when it's at the end of a word and not part of a number
    normalized = re.sub(r"([a-zA-Z0-9]+)%\b", r"\1", normalized)
    
    # Also handle standalone % at end of content
    normalized = re.sub(r"%$", "", normalized)
    
    # Clean up orphaned LaTeX space sequences after percent removal
    normalized = re.sub(r"\\,\s*$", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized


def _math_label(value: str) -> str:
    label = str(value or "").replace("_", " ")
    label = re.sub(r"\s+", " ", label.replace(r"\ ", " ")).strip()
    label = label.replace(r"\,", " ")
    label = re.sub(r"\s+", " ", label).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", label):
        return label
    # Apply business label normalization before wrapping in \mathrm{}
    label = _normalize_business_label_in_latex(label)
    return r"\mathrm{{{}}}".format(label.replace(" ", r"\,"))


def _plain_latex_label(value: str) -> str:
    label = str(value or "").strip()
    label = re.sub(r"\\(?:mathrm|text)\s*\{([^{}]+)\}", r"\1", label)
    label = label.replace(r"\,", " ").replace(r"\ ", " ")
    label = re.sub(r"\\[A-Za-z]+\b", "", label)
    label = re.sub(r"[{}]", "", label)
    label = re.sub(r"\s+", " ", label).strip()
    return label


def _is_simple_latex_operand(value: str) -> bool:
    candidate = str(value or "").strip()
    stripped = re.sub(r"\\(?:mathrm|text)\s*\{[^{}]+\}", "", candidate)
    return not re.search(r"\\[A-Za-z]+|[_^{}()]|[+\-*/=]", stripped)


def _extract_simple_latex_fraction(latex: str) -> tuple[str, str, str | None] | None:
    frac_pos = latex.find(r"\frac")
    if frac_pos < 0:
        return None

    def read_group(start: int) -> tuple[str, int] | None:
        if start >= len(latex) or latex[start] != "{":
            return None
        depth = 0
        for idx in range(start, len(latex)):
            ch = latex[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return latex[start + 1 : idx], idx + 1
        return None

    idx = frac_pos + len(r"\frac")
    while idx < len(latex) and latex[idx].isspace():
        idx += 1
    numerator_group = read_group(idx)
    if not numerator_group:
        return None
    numerator, idx = numerator_group
    while idx < len(latex) and latex[idx].isspace():
        idx += 1
    denominator_group = read_group(idx)
    if not denominator_group:
        return None
    denominator, idx = denominator_group
    if not (_is_simple_latex_operand(numerator) and _is_simple_latex_operand(denominator)):
        return None
    tail = latex[idx:]
    scale_match = re.search(r"(?:(?:\\times|×|\*)\s*)?(\d+(?:\.\d+)?)\s*$", tail)
    scale = scale_match.group(1) if scale_match and re.search(r"(?:\\times|×|\*)", tail) else None
    return numerator, denominator, scale


def _formula_notes_html(notes: list[str]) -> str:
    if not notes:
        return ""
    return "<p><b>Where:</b></p><ul>" + "".join(f"<li>{n}</li>" for n in notes) + "</ul>"


def _canonical_formula_html(latex: str, notes: list[str] | None = None) -> str:
    return f'<div class="math-equation">\\[ {latex} \\]</div>{_formula_notes_html(notes or [])}'


def _missing_formula_html() -> str:
    return (
        '<div class="formula-evidence-note">'
        "<strong>Formal formula not declared in source evidence.</strong> "
        "Review the executable context in Evidence &amp; Lineage before executive use."
        "</div>"
    )


def _latex_formula_html(value: str) -> dict:
    latex = _normalize_latex_formula(value)
    notes = []
    ratio = _extract_simple_latex_fraction(latex)
    if ratio:
        numerator, denominator, scale = ratio
        notes = [
            f"<i>Numerator:</i> {_plain_latex_label(numerator)}",
            f"<i>Denominator:</i> {_plain_latex_label(denominator)}",
        ]
        if scale:
            notes.append(f"<i>Scale:</i> ×{scale}")
    return {
        "formula_html": _canonical_formula_html(latex, notes),
        "formula_expression": latex,
        "formula_result_name": "",
    }


def format_text_as_html_list(text: str) -> str:
    from html import escape

    cleaned = _sanitize_text(text)
    safe = escape(cleaned)
    if not safe or "Error generating content" in safe:
        return f"<p>{safe}</p>"
    bullet_items = re.findall(r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+(.+)", cleaned)
    if bullet_items:
        items = [escape(i.strip()) for i in bullet_items if len(i.strip()) > 1]
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    return f"<p>{safe}</p>"


def _extract_function_block(code_context: str, anchor_line_number: int):
    import ast

    lines = code_context.splitlines()
    if not lines or anchor_line_number <= 0 or anchor_line_number > len(lines):
        return code_context, 0
    try:
        tree = ast.parse(code_context)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                start = node.lineno
                end = getattr(node, "end_lineno", None)
                if end is None:
                    last = node.body[-1]
                    end = getattr(last, "end_lineno", getattr(last, "lineno", start))
                if start <= anchor_line_number <= end:
                    return "\n".join(lines[start - 1 : end]), start - 1
    except Exception:
        pass
    anchor_idx = anchor_line_number - 1
    start_idx = -1
    for i in range(anchor_idx, -1, -1):
        if lines[i].lstrip().startswith("def "):
            start_idx = i
            break
    if start_idx == -1:
        for i in range(anchor_idx, len(lines)):
            if lines[i].lstrip().startswith("def "):
                start_idx = i
                break
    if start_idx == -1:
        return code_context, 0
    def_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        raw = lines[j]
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if not stripped:
            continue
        if raw.lstrip().startswith("def ") and indent <= def_indent:
            end_idx = j
            break
        if indent < def_indent:
            end_idx = j
            break
        if indent == 0 and (
            stripped.startswith("#") or stripped.startswith("if __name__")
        ):
            end_idx = j
            break
    scoped = "\n".join(lines[start_idx:end_idx])
    return scoped, start_idx


def generate_formula_from_code(code_context: str) -> dict:
    """
    Programmatically generate a MathJax block from code context.
    Supports:
    - DAX: DEFINE MEASURE 'T'[Name] = ... RETURN <expr> | Name = <expr>
    - SQL/T-SQL/HANA: SELECT <expr> AS <alias> (multi-line, CAST/CASE supported)
    - C#/VB/PLSQL/ABAP: return <expr>; or <var> = <expr>;
    - IEC 61131-3 ST: <var> := <expr>;
    - Generic fallback: pick the most math-like expression (percent or division) anywhere in the block.
    """
    formula_data = {
        "formula_html": _missing_formula_html(),
        "formula_expression": "",
        "formula_result_name": "",
    }

    ctx = code_context

    # 0) Helpers

    def latex_escape(s: str) -> str:
        repl = [
            ("\\", r"\\"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("_", r"\_"),
            ("^", r"\^"),
            ("~", r"\~"),
        ]
        out = s
        for a, b in repl:
            out = out.replace(a, b)
        return out

    def sanitize_token(t: str) -> str:
        t = t.strip()
        t = re.sub(r"^[{}\[\];,\s]+|[{}\[\];,\s]+$", "", t)
        t = re.sub(r"^\s*#\s*", "Number of ", t)
        t = re.sub(r"^\s*%\s*", "Percent ", t)
        t = re.sub(r"^\s*\$\s*", "Dollar ", t)
        t = t.replace("#", " Number ")
        t = t.replace("$", " Dollar ")
        t = re.sub(r"%\s*([A-Za-z])", r"Percent \1", t)
        t = re.sub(r"\s+%", "", t)
        t = t.replace("%", " Percent ")
        t = t.replace("&", " and ")
        t = re.sub(r"[:\.]+", " ", t)
        t = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", t)
        t = t.replace("_", " ")
        t = re.sub(r"(?i)(maintenance)to(operating)", r"\1 to \2", t)
        t = re.sub(r"(?i)(cost)ratio", r"\1 ratio", t)
        t = re.sub(r"(?i)(feedstock)throughput", r"\1 throughput", t)
        t = re.sub(r"(?i)(error)rate", r"\1 rate", t)
        t = re.sub(r"(?i)(extraction)rate", r"\1 rate", t)
        t = re.sub(r"\s+", " ", t).strip()
        t = latex_escape(t)
        title = t.title()
        title = re.sub(r"\bOee\b", "OEE", title)
        title = re.sub(r"\bNps\b", "NPS", title)
        title = re.sub(r"\bKpi\b", "KPI", title)
        title = re.sub(r"\bHse\b", "HSE", title)
        return title

    def L(v: str) -> str:
        return _math_label(v)

    def strip_inline_comments(line: str) -> str:
        cleaned = line
        cleaned = re.split(r"--", cleaned, maxsplit=1)[0]
        cleaned = re.split(r"//", cleaned, maxsplit=1)[0]
        cleaned = re.split(r"\(\*", cleaned, maxsplit=1)[0]
        cleaned = re.split(r"(?<!:)\s'", cleaned, maxsplit=1)[0]
        cleaned = re.split(r"#", cleaned, maxsplit=1)[0]
        return cleaned.rstrip(" ;\t")

    def unwrap_sql_expr(expr: str) -> str:
        e = expr.strip()
        m = re.search(r"(?is)\bCAST\s*\(\s*(?P<inner>.+?)\s+AS\s+[^\)]+\)", e)
        if m:
            e = m.group("inner").strip()
        m = re.search(r"(?is)\bCOALESCE\s*\(\s*(?P<inner>.+?)\s*,\s*.+?\)", e)
        if m:
            e = m.group("inner").strip()
        e = re.sub(r"(?is)\bNULLIF\s*\(\s*(.+?)\s*,\s*.+?\)", r"\1", e)
        e = re.sub(r"[;{}]+$", "", e).strip()
        return strip_wrapping_parentheses(e)

    def normalize_sql_guards(expr: str) -> str:
        e = str(expr or "")
        previous = None
        while previous != e:
            previous = e
            e = re.sub(
                r"(?is)\bNULLIF\s*\(\s*(?P<inner>[^,()]+(?:\([^()]*\))?)\s*,\s*0(?:\.0)?\s*\)",
                r"\g<inner>",
                e,
            )
            e = re.sub(
                r"(?is)\bCOALESCE\s*\(\s*(?P<inner>[^,()]+(?:\([^()]*\))?)\s*,\s*[^()]+?\)",
                r"\g<inner>",
                e,
            )
        return e

    def is_invalid_formula_candidate(expr: str) -> bool:
        e = str(expr or "").strip()
        if not e:
            return True
        if e == "/" or re.fullmatch(r"/+\s*", e):
            return True
        if re.fullmatch(r"[+\-*/×÷();,\s]+", e):
            return True
        if e.lower() in {"nullif", "cast", "case", "end"}:
            return True
        return False

    def strip_wrapping_parentheses(expr: str) -> str:
        e = expr.strip()
        while e.startswith("(") and e.endswith(")"):
            depth = 0
            wraps_entire_expr = True
            for idx, ch in enumerate(e):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and idx != len(e) - 1:
                        wraps_entire_expr = False
                        break
            if not wraps_entire_expr:
                break
            e = e[1:-1].strip()
        return e

    def balance_parentheses(expr: str) -> str:
        e = expr.strip()
        while e.count(")") > e.count("(") and ")" in e:
            e = e[: e.rfind(")")] + e[e.rfind(")") + 1 :]
        while e.count("(") > e.count(")") and "(" in e:
            e = e[: e.find("(")] + e[e.find("(") + 1 :]
        return e.strip()

    def normalize_expression(expr: str) -> str:
        e = expr.strip()
        assignment_parts = re.split(r"(?<![<>!])=(?!=)", e)
        if len(assignment_parts) > 1 and is_math_like(assignment_parts[-1]):
            e = assignment_parts[-1].strip()
        e = e.replace("×", "*").replace("÷", "/")
        e = re.sub(r"(?i)\bdivided\s+by\b", "/", e)
        e = re.sub(r"(?i)\bmultiplied\s+by\b", "*", e)
        e = re.sub(r"(?i)\bminus\b", "-", e)
        e = re.sub(r"(?i)\bplus\b", "+", e)
        e = re.sub(r"(?i)\s+based\s+on\b.*$", "", e)
        e = normalize_sql_guards(e)
        e = balance_parentheses(e)
        return e

    def split_top_level_operator(expr: str, operators: set[str]) -> tuple[str, str, str] | None:
        depth = 0
        for idx in range(len(expr) - 1, -1, -1):
            ch = expr[idx]
            if ch == "(":
                depth = max(depth - 1, 0)
            elif ch == ")":
                depth += 1
            elif ch in operators and depth == 0:
                if ch in {"+", "-"} and idx == 0:
                    continue
                lhs = expr[:idx].strip()
                rhs = expr[idx + 1 :].strip()
                if lhs and rhs:
                    return lhs, ch, rhs
        return None

    def split_top_level_division(expr: str) -> tuple[str, str] | None:
        split = split_top_level_operator(expr, {"/"})
        if split:
            return split[0], split[2]
        return None

    def split_top_level_product(expr: str) -> list[str]:
        parts = []
        depth = 0
        start = 0
        for idx, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(depth - 1, 0)
            elif ch == "*" and depth == 0:
                part = expr[start:idx].strip()
                if part:
                    parts.append(part)
                start = idx + 1
        tail = expr[start:].strip()
        if tail:
            parts.append(tail)
        return parts

    def clean_operand(value: str) -> str:
        v = strip_wrapping_parentheses(normalize_expression(value))
        v = unwrap_sql_expr(v)
        v = re.sub(r"(?is)\bNULLIF\s*\(\s*(?P<inner>.+?)\s*,\s*0(?:\.0)?\s*\)", r"\g<inner>", v)
        v = re.sub(r"(?is)\bCOALESCE\s*\(\s*(?P<inner>.+?)\s*,\s*.+?\)", r"\g<inner>", v)
        v = re.sub(
            r"(?is)\b(?:SUM|AVG|MIN|MAX)\s*\(\s*(?P<inner>.+?)\s*\)",
            r"\g<inner>",
            v,
        )
        v = re.sub(r"(?is)\bCOUNT\s*\(\s*\*\s*\)", "Count", v)
        v = re.sub(r"(?is)\bCAST\s*\(\s*(?P<inner>.+?)\s+AS\s+.+?\)", r"\g<inner>", v)
        v = re.sub(r"(?is)\bDATEDIFF\s*\(.+?\)", "Date Difference", v)
        v = strip_wrapping_parentheses(v)
        return v.strip()

    def is_math_like(expr: str) -> bool:
        return bool(expr) and (
            any(op in expr for op in ("+", "-", "*", "/", "%", "×", "÷"))
            or bool(
                re.search(
                    r"(?i)\b(?:minus|plus|divided\s+by|multiplied\s+by)\b",
                    expr,
                )
            )
        )

    def is_weak_expr(expr: str) -> bool:
        e = clean_operand(expr).strip()
        if is_invalid_formula_candidate(e):
            return True
        if re.fullmatch(r"\d+(?:\.\d+)?", e):
            return True
        if re.search(r"(?i)\bplaceholder\b", e):
            return True
        if e.lower() in {"number", "return number"}:
            return True
        if e.lower() in {"nullif", "cast"}:
            return True
        return False

    def is_numeric_literal(value: str) -> bool:
        return bool(re.fullmatch(r"\d+(?:\.\d+)?", value.strip()))

    def to_business_label(var_name: str) -> str:
        if re.fullmatch(r"\d+(?:\.\d+)?", var_name.strip()):
            return var_name.strip()
        clean = var_name.strip()
        clean = re.sub(r'_(?:tons|pct|percent|hours|tons_day|tons_per_day|c|celsius|variance|variance_pct|cost_ratio|variance_variance)$', '', clean, flags=re.I)
        clean = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", clean.replace('_', ' '))
        words = []
        for w in clean.split():
            if w.lower() in {'pct', 'tons', 'tonnes', 'kg', 'm3', 'per', 'day', 'c'}:
                continue
            words.append(w.capitalize())
        label = " ".join(words)
        special_mappings = {
            "Ethylene Produced": "Ethylene Produced",
            "Feedstock Input": "Feedstock Input",
            "Revenue": "Revenue",
            "Cost": "Cost",
            "Operating Time": "Operating Time",
            "Failure Count": "Failure Count",
            "Operating Hours": "Operating Time",
            "Number Of Failures": "Failure Count",
        }
        return special_mappings.get(label, label)

    class Node:
        pass

    class NumberNode(Node):
        def __init__(self, value):
            self.value = value
        def to_latex(self):
            return self.value

    class VarNode(Node):
        def __init__(self, name):
            self.name = name
        def to_latex(self):
            return _math_label(to_business_label(self.name))

    class BinOpNode(Node):
        def __init__(self, left, op, right):
            self.left = left
            self.op = op
            self.right = right
        def to_latex(self):
            l_str = self.left.to_latex()
            r_str = self.right.to_latex()
            if self.op == '/':
                return r"\frac{{{}}}{{{}}}".format(l_str, r_str)
            elif self.op == '*':
                return r"{} \times {}".format(l_str, r_str)
            elif self.op == '^':
                return r"{}^{{{}}}".format(l_str, r_str)
            else:
                return r"{} {} {}".format(l_str, self.op, r_str)

    class ParenthesisNode(Node):
        def __init__(self, node):
            self.node = node
        def to_latex(self):
            return r"\left({}\right)".format(self.node.to_latex())

    def tokenize(expr: str) -> list[str]:
        expr = expr.replace("×", "*").replace("÷", "/")
        token_re = re.compile(r'(\d+(?:\.\d+)?|[a-zA-Z_][a-zA-Z0-9_]*(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)*|[+\-*/^()])')
        tokens = []
        for m in token_re.finditer(expr):
            t = m.group(0).strip()
            if t:
                tokens.append(t)
        return tokens

    def parse_expression_nodes(tokens: list[str]) -> Node:
        idx = [0]
        def peek():
            if idx[0] < len(tokens):
                return tokens[idx[0]]
            return None
        def consume():
            t = peek()
            idx[0] += 1
            return t
        def parse_primary():
            t = peek()
            if t == '(':
                consume()
                node = parse_expr()
                consume()
                return ParenthesisNode(node)
            elif t and (t.replace('.', '', 1).isdigit()):
                consume()
                return NumberNode(t)
            elif t and (t not in {'+', '-', '*', '/', '^', ')'}):
                consume()
                return VarNode(t)
            else:
                raise ValueError(f"Unexpected token: {t}")
        def parse_exponent():
            node = parse_primary()
            while peek() == '^':
                op = consume()
                right = parse_primary()
                node = BinOpNode(node, op, right)
            return node
        def parse_term():
            node = parse_exponent()
            while peek() in {'*', '/'}:
                op = consume()
                right = parse_exponent()
                node = BinOpNode(node, op, right)
            return node
        def parse_expr():
            node = parse_term()
            while peek() in {'+', '-'}:
                op = consume()
                right = parse_term()
                node = BinOpNode(node, op, right)
            return node
        node = parse_expr()
        if idx[0] < len(tokens):
            raise ValueError("Extra tokens")
        return node

    def parse_to_latex(expr_str: str) -> str:
        if any(ph in expr_str.lower() for ph in {"sum of", "count of", "average of"}):
            raise ValueError("Aggregations should use old rendering path")
        e_clean = normalize_sql_guards(expr_str)
        e_clean = re.sub(r'\s*\(\s*(?:tons|percent|hours|tons/day|c|celsius|%|°c|celsius)\s*\)', '', e_clean, flags=re.I)
        tokens = tokenize(e_clean)
        if not tokens:
            raise ValueError("No tokens found")
        node = parse_expression_nodes(tokens)
        return node.to_latex()

    def render_latex_expr(expr: str) -> str:
        e = clean_operand(expr)
        if not e:
            return L("Value")
        try:
            return parse_to_latex(e)
        except Exception:
            sum_match = re.match(r"(?is)^sum\s+of\s+(?:all\s+)?(?P<item>.+)$", e)
            if sum_match:
                return r"\sum {}".format(_math_label(sanitize_token(sum_match.group("item"))))
            count_match = re.match(r"(?is)^count\s+of\s+(?P<item>.+)$", e)
            if count_match:
                return r"\operatorname{{count}}\left({}\right)".format(
                    _math_label(sanitize_token(count_match.group("item")))
                )
            avg_match = re.match(r"(?is)^average\s+of\s+(?P<item>.+)$", e)
            if avg_match:
                return r"\operatorname{{avg}}\left({}\right)".format(
                    render_latex_expr(avg_match.group("item"))
                )
            split = split_top_level_operator(e, {"+", "-"})
            if split:
                lhs, op, rhs = split
                return f"{render_latex_expr(lhs)} {op} {render_latex_expr(rhs)}"
            split = split_top_level_operator(e, {"/"})
            if split:
                lhs, _, rhs = split
                return r"\frac{{{}}}{{{}}}".format(
                    render_latex_expr(lhs), render_latex_expr(rhs)
                )
            product_parts = split_top_level_product(e)
            if len(product_parts) > 1:
                return r" \times ".join(render_latex_expr(p) for p in product_parts)
            if is_numeric_literal(e):
                return e
            return L(sanitize_token(e))

    def note_label(expr: str) -> str:
        label = clean_operand(expr)
        label = re.sub(r"[:]+", " ", label)
        label = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", label)
        label = label.replace("_", " ")
        label = re.sub(r"\s+", " ", label).strip()
        return label.title()

    def split_ratio_and_scale(expr: str) -> tuple[str, str, str | None] | None:
        e = strip_wrapping_parentheses(normalize_expression(expr))
        scale = None
        product = split_top_level_product(e)
        if len(product) > 1:
            numeric_parts = [p for p in product if re.fullmatch(r"\d+(?:\.\d+)?", strip_wrapping_parentheses(p))]
            ratio_parts = [p for p in product if split_top_level_division(strip_wrapping_parentheses(p))]
            if numeric_parts and ratio_parts:
                scale = numeric_parts[-1]
                e = strip_wrapping_parentheses(ratio_parts[0])
        leading_scale = re.match(r"(?is)^\s*(?P<scale>\d+(?:\.\d+)?)\s*\*\s*(?P<ratio>.+)$", e)
        if leading_scale and split_top_level_division(strip_wrapping_parentheses(leading_scale.group("ratio"))):
            scale = leading_scale.group("scale")
            e = strip_wrapping_parentheses(leading_scale.group("ratio"))
        divisor = split_top_level_division(strip_wrapping_parentheses(e))
        if not divisor:
            return None
        return divisor[0], divisor[1], scale

    def compact_result_label(name: str) -> str:
        label = note_label(_business_display_name(name))
        label = re.sub(r"\s*\(\s*(?:%|Percent|Percentage)\s*\)\s*$", "", label, flags=re.I)
        label = re.sub(r"\s+Percent\s*$", "", label, flags=re.I)
        label = re.sub(r"^\s*[#%$]+\s*", "", label).strip()
        label = re.sub(r"(?i)^(?:Number|No\.?)\s+Of\s+", "", label).strip()
        label = re.sub(r"(?i)^Number\s+", "", label).strip()
        label = re.sub(r"(?i)^Percent\s+", "", label).strip()
        label = re.sub(r"(?i)^Dollar\s+", "", label).strip()
        label = re.sub(r"\s+", " ", label).strip()
        words = label.split()
        if len(words) > 4:
            label = " ".join(words[-4:])
        return label or "KPI"

    def aggregate_match(expr: str) -> tuple[str, str] | None:
        e = clean_operand(expr)
        m = re.match(r"(?is)^sum\s+of\s+(?:all\s+)?(?P<item>.+)$", e)
        if m:
            return "sum", note_label(m.group("item"))
        m = re.match(r"(?is)^count\s+of\s+(?:all\s+)?(?P<item>.+)$", e)
        if m:
            return "count", note_label(m.group("item"))
        m = re.match(r"(?is)^average\s+of\s+(?P<item>.+)$", e)
        if m:
            return "avg", note_label(m.group("item"))
        return None

    def find_top_level_as_positions(text: str) -> list[int]:
        positions = []
        depth = 0
        for m in re.finditer(r"(?is)\(|\)|\bAS\b", text):
            token = m.group(0).upper()
            if token == "(":
                depth += 1
            elif token == ")":
                depth = max(depth - 1, 0)
            elif depth == 0:
                positions.append(m.start())
        return positions

    def split_top_level_commas(text: str) -> list[str]:
        parts: list[str] = []
        depth = 0
        start = 0
        for idx, ch in enumerate(text):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(depth - 1, 0)
            elif ch == "," and depth == 0:
                part = text[start:idx].strip()
                if part:
                    parts.append(part)
                start = idx + 1
        tail = text[start:].strip()
        if tail:
            parts.append(tail)
        return parts

    def extract_select_clauses(text: str) -> list[str]:
        clauses = []
        source = "\n".join(
            line for line in (text or "").splitlines()
            if not line.strip().startswith(("--", "#", "//", "*"))
        )
        select_re = re.compile(r"(?is)\bSELECT\b")
        from_re = re.compile(r"(?is)\bFROM\b")
        for match in select_re.finditer(source):
            start = match.end()
            depth = 0
            end = None
            idx = start
            while idx < len(source):
                ch = source[idx]
                if ch == "(":
                    depth += 1
                    idx += 1
                    continue
                if ch == ")":
                    depth = max(depth - 1, 0)
                    idx += 1
                    continue
                if depth == 0:
                    fm = from_re.match(source, idx)
                    if fm:
                        end = idx
                        break
                    if source[idx] == ";":
                        end = idx
                        break
                idx += 1
            if end is None:
                end = len(source)
            clause = source[start:end].strip()
            if clause:
                clauses.extend(split_top_level_commas(clause))
        return clauses

    def extract_calculation_hint(text: str) -> tuple[str | None, str | None]:
        def inferred_result_name() -> str:
            kpi_match = re.search(
                r"(?im)^\s*(?:--|#|//|/\*+|\*)\s*KPI\s*:?\s*(?P<name>.+?)\s*(?:\*/)?\s*$",
                text or "",
            )
            if kpi_match:
                name = kpi_match.group("name").strip()
                return _normalize_business_identifier(name)
            function_match = re.search(
                r"(?is)\bFUNCTION\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+RETURN\s+NUMBER\b",
                text or "",
            )
            if function_match:
                name = function_match.group("name").strip()
                return _normalize_business_identifier(name)
            return "Result"

        hint_re = re.compile(
            r"(?im)^\s*(?:--|#|//|/\*+|\*)\s*"
            r"(?:Formula|Business\s+Formula|Body\s+hint|Body\s+computes|Computes|Calculation)\s*:?\s*"
            r"(?P<expr>.+?)\s*(?:\*/)?\s*$"
        )
        for match in hint_re.finditer(text or ""):
            expr = match.group("expr").strip()
            expr = re.sub(r"(?is)^\s*(?:=|:)\s*", "", expr)
            if is_invalid_formula_candidate(expr):
                continue
            if is_math_like(expr):
                return inferred_result_name(), expr
        # Return the KPI name even if no formula hint found (for use as fallback result name)
        kpi_name = inferred_result_name()
        if kpi_name != "Result":
            return kpi_name, None
        return None, None

    def extract_nps_formula(text: str) -> tuple[str | None, str | None]:
        source = text or ""
        has_promoter = re.search(
            r"(?is)SUM\s*\(\s*CASE\s+WHEN\s+[^)]*score[^)]*>=\s*9\s+THEN\s+1\s+ELSE\s+0\s+END\s*\)",
            source,
        )
        has_detractor = re.search(
            r"(?is)SUM\s*\(\s*CASE\s+WHEN\s+[^)]*score[^)]*<=\s*6\s+THEN\s+1\s+ELSE\s+0\s+END\s*\)",
            source,
        )
        has_count = re.search(r"(?is)\bCOUNT\s*\(\s*\*\s*\)", source)
        has_nps_name = re.search(r"(?is)\b(?:NPS|Net\s+Promoter)", source)
        if has_promoter and has_detractor and has_count and has_nps_name:
            return "NPS", "(Promoter Count - Detractor Count) / Total Responses * 100"
        return None, None

    def extract_structured_expression(text: str) -> tuple[str | None, str | None]:
        source = text or ""
        pair_re = re.compile(
            r'"name"\s*:\s*"(?P<name>[^"]+)"\s*,\s*"expression"\s*:\s*"(?P<expr>(?:\\.|[^"])*)"'
            r'|'
            r'"expression"\s*:\s*"(?P<expr_first>(?:\\.|[^"])*)"\s*,\s*"name"\s*:\s*"(?P<name_after>[^"]+)"',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pair_re.finditer(source):
            name = match.groupdict().get("name") or match.groupdict().get("name_after") or "Result"
            expr = match.groupdict().get("expr") or match.groupdict().get("expr_first") or ""
            expr = expr.encode("utf-8").decode("unicode_escape")
            if expr and is_math_like(expr) and not is_invalid_formula_candidate(expr):
                return name, expr
        expr_re = re.compile(
            r'"expression"\s*:\s*"(?P<expr>(?:\\.|[^"])*)"',
            re.IGNORECASE | re.DOTALL,
        )
        for match in expr_re.finditer(source):
            expr = match.group("expr").encode("utf-8").decode("unicode_escape")
            if expr and is_math_like(expr) and not is_invalid_formula_candidate(expr):
                return "Result", expr
        return None, None

    def gd(m: re.Match | None, key: str, default: str = "") -> str:
        if not m:
            return default
        try:
            return m.groupdict().get(key, default)
        except Exception:
            return default

    # Prepare cleaned single lines for non-multiline patterns
    cleaned_lines = []
    for raw in ctx.splitlines():
        s = raw.strip()
        if not s or s.startswith(("#", "--", "//", "/*", "*", "'")):
            continue
        cleaned_lines.append(strip_inline_comments(raw).strip())

    # Improved extraction: handle SQL aliases properly
    def extract_result_name_and_expression(text: str) -> tuple[str | None, str | None]:
        """
        Scan the entire text for a plausible result name and a math expression.
        Returns (result_name, expression) or (None, None).
        """
        result_name = "Result"
        math_expr = None

        # Explicit formula/calculation comments are business-owned evidence and
        # must outrank package delimiters, declarations, and generic SQL scans.
        hint_name, hint_expr = extract_calculation_hint(text)
        if hint_name:
            result_name = hint_name
            if hint_expr:
                return result_name, hint_expr
            # If we have a KPI name but no formula hint, keep the name and continue
            # to find an expression from other sources

        result_name, math_expr = extract_nps_formula(text)
        if result_name and math_expr:
            return result_name, math_expr

        result_name, math_expr = extract_structured_expression(text)
        if result_name and math_expr:
            return result_name, math_expr

        # If we have a KPI name from hint but no expression yet, use it as result_name
        # and continue looking for expression
        if hint_name and hint_name != "Result":
            result_name = hint_name
        else:
            result_name = "Result"
        math_expr = None

        # Look for AS alias first (SQL/HANA). Prefer top-level SELECT clauses that
        # actually calculate something, not nested helper SELECTs.
        select_clauses = extract_select_clauses(text)
        scored_clauses = sorted(
            select_clauses,
            key=lambda c: (
                1 if is_math_like(c) else 0,
                1 if find_top_level_as_positions(c) else 0,
                -len(c),
            ),
            reverse=True,
        )
        for select_clause in scored_clauses:
            # Find the last top-level AS (not inside parentheses)
            # We'll find all AS occurrences and pick the last one not inside parentheses
            as_positions = find_top_level_as_positions(select_clause)
            if as_positions:
                last_as = as_positions[-1]
                alias = select_clause[last_as + 2 :].strip()
                # Clean alias (remove brackets, quotes, etc.)
                alias = re.sub(r'^[\[\("\']|[\]\)"\']$', "", alias)
                if alias:
                    result_name = alias
                expr = select_clause[:last_as].strip()
            else:
                expr = select_clause
            # Remove outer parentheses
            expr = strip_wrapping_parentheses(expr)
            # Unwrap SQL functions
            expr = unwrap_sql_expr(expr)
            if is_invalid_formula_candidate(expr):
                continue
            if expr and (not is_weak_expr(expr) or re.search(r"(?is)\bCOUNT\s*\(\s*\*\s*\)", expr)):
                return result_name, expr
            if expr and result_name != "Result" and not is_invalid_formula_candidate(expr):
                return result_name, expr

        # Look for DAX measure definition
        dax_match = re.search(
            r"(?is)\bDEFINE\s+MEASURE\s+[^\[]*\[(?P<name>[^\]]+)\]\s*=\s*(?P<body>.+?)(?:$|\n\s*\n)",
            text,
        )
        if dax_match:
            name = gd(dax_match, "name")
            body = gd(dax_match, "body")
            if name and body:
                ret = re.search(r"(?is)\bRETURN\b\s*(?P<expr>.+)", body)
                if ret:
                    expr = gd(ret, "expr")
                    if expr and not is_invalid_formula_candidate(expr):
                        return name, expr

        # Human formula text such as "Propylene to Ethylene (P/E) Ratio = A / B".
        human_assign = re.search(
            r"(?im)^\s*(?P<lhs>[^=\r\n]{1,120}?)\s*=\s*(?P<expr>.+?)(?:$|;|\n)",
            text,
        )
        if human_assign:
            lhs = human_assign.group("lhs").strip()
            expr = human_assign.group("expr").strip()
            if not re.match(r"^\s*(?:#|//|--|/\*|\*)", lhs) and expr and (
                is_math_like(expr)
                or re.match(r"(?is)^\s*(?:sum|count)\s+of\b", expr)
            ):
                # Normalize the business identifier (LHS)
                normalized_lhs = _normalize_business_identifier(lhs)
                return normalized_lhs, expr

        # Look for simple assignments like "x = a / b" (Python, C#, etc.)
        assign_matches = list(
            re.finditer(
                r"(?im)^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?P<expr>.+?)(?:$|;|\n)",
                text,
            )
        )
        assign_matches.sort(
            key=lambda m: (is_math_like(m.group("expr")), not is_weak_expr(m.group("expr"))),
            reverse=True,
        )
        for assign_pattern in assign_matches:
            lhs = assign_pattern.group(1)
            expr = strip_inline_comments(assign_pattern.group("expr").strip())
            if expr and not is_invalid_formula_candidate(expr) and (is_math_like(expr) or not is_weak_expr(expr)):
                if result_name == "Result":
                    result_name = lhs
                return result_name, expr

        # Look for IEC ST assignment :=
        st_match = re.search(
            r"(?im)^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:=\s*(?P<expr>.+?)(?:$|;|\n)", text
        )
        if st_match:
            lhs = st_match.group(1)
            expr = st_match.group("expr").strip()
            if expr and not is_invalid_formula_candidate(expr):
                if result_name == "Result":
                    result_name = lhs
                return result_name, expr

        # Look for return statements
        return_matches = list(re.finditer(r"(?im)\breturn\b\s+(?P<expr>[^;\r\n]+)", text))
        return_matches.sort(
            key=lambda m: (is_math_like(m.group("expr")), not is_weak_expr(m.group("expr"))),
            reverse=True,
        )
        for ret_match in return_matches:
            expr = ret_match.group("expr").strip()
            if expr and not is_invalid_formula_candidate(expr) and (is_math_like(expr) or not is_weak_expr(expr)):
                return result_name, expr

        # If nothing, look for any line with a fraction or percent pattern
        pct_lines = re.findall(
            r"(?is)(\d*\.?\d+\s*\*\s*100|100\s*\*\s*\d*\.?\d+)", text
        )
        if pct_lines:
            expr = pct_lines[0]
            return result_name, expr

        # Look for any division or multiplication
        div_match = re.search(
            r"(?is)([a-zA-Z0-9_\.\s]+)\s*/\s*([a-zA-Z0-9_\.\s]+)", text
        )
        if div_match:
            a, b = div_match.groups()
            expr = f"{a.strip()} / {b.strip()}"
            if not is_invalid_formula_candidate(expr):
                return result_name, expr

        return None, None

    def build_html(result_var: str, expression: str) -> dict:
        rv = sanitize_token(compact_result_label(result_var))
        expr = strip_wrapping_parentheses(normalize_expression(expression.strip().rstrip(";")))
        notes = []
        aggregate = aggregate_match(expr)
        # Normalize the result variable before generating LaTeX
        normalized_rv = _normalize_business_identifier(rv) if rv else rv
        if aggregate:
            aggregate_type, aggregate_item = aggregate
            if aggregate_type == "sum":
                latex_str = r"{} = \sum_{{i=1}}^{{N}} 1".format(L(normalized_rv))
            elif aggregate_type == "count":
                latex_str = r"{} = \operatorname{{count}}(T)".format(L(normalized_rv))
            else:
                latex_str = r"{} = {}".format(L(normalized_rv), render_latex_expr(expr))
            if aggregate_type == "avg":
                notes = [
                    f"<i>Expression:</i> {aggregate_item}",
                    "<i>Rule:</i> Average the calculated value across qualifying records in the reporting period.",
                ]
            else:
                notes = [
                    f"<i>N / T:</i> {aggregate_item}",
                    "<i>Rule:</i> Count each qualifying record once in the reporting period.",
                ]
        else:
            latex_str = r"{} = {}".format(L(normalized_rv), render_latex_expr(expr))

        ratio = split_ratio_and_scale(expr)
        if ratio and not aggregate:
            numerator, denominator, scale = ratio
            notes = [
                f"<i>Numerator:</i> {note_label(numerator)}",
                f"<i>Denominator:</i> {note_label(denominator)}",
            ]
            if scale:
                notes.append(f"<i>Scale:</i> ×{note_label(scale)}")

        if latex_str:
            notes_html = (
                _formula_notes_html(notes)
            )
            return {
                "formula_html": _canonical_formula_html(latex_str, notes),
                "formula_expression": expr,
                "formula_result_name": normalized_rv,
            }

        return {"formula_html": _missing_formula_html()}

    # --- Main extraction ---
    result_name, math_expr = extract_result_name_and_expression(ctx)
    if result_name and math_expr:
        return build_html(result_name, math_expr)

    # Fallback: try to find any math-like expression in cleaned lines
    for line in cleaned_lines:
        if is_invalid_formula_candidate(line):
            continue
        if "/" in line or "*" in line:
            match = re.search(r"([a-zA-Z0-9_\.\s]+)\s*/\s*([a-zA-Z0-9_\.\s]+)", line)
            if match:
                a, b = match.groups()
                expr = f"{a.strip()} / {b.strip()}"
                name_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=", line)
                res_name = "Result"
                if name_match:
                    res_name = sanitize_token(name_match.group(1))
                return build_html(res_name, expr)

    return formula_data


def create_rst_file(
    kpi_data: dict,
    details: dict,
    template: jinja2.Template,
    ai_time_seconds: float | None = None,
):
    from html import escape
    import time

    render_start = time.perf_counter()
    kpi_line_in_context = 0
    context_lines = (kpi_data.get("code_context") or "").split("\n")
    kpi_name = kpi_data.get("name") or ""
    kpi_display_name = kpi_data.get("display_name") or _business_display_name(kpi_name)
    kpi_data["display_name"] = kpi_display_name
    kpi_data["raw_name"] = kpi_data.get("raw_name") or kpi_name
    kpi_data["name_was_normalized"] = bool(kpi_name and kpi_display_name != kpi_name)
    for i, line in enumerate(context_lines):
        if (
            f"# KPI: {kpi_name}" in line
            or f"-- KPI: {kpi_name}" in line
            or f"' KPI: {kpi_name}" in line
            or f"/* KPI: {kpi_name}" in line
        ):
            kpi_line_in_context = i + 1
            break
    kpi_data["context_line_number"] = kpi_line_in_context
    file_path = kpi_data.get("file_path") or ""
    try:
        source_line_number = int(
            kpi_data.get("file_line") or kpi_data.get("context_line_number") or 1
        )
    except (TypeError, ValueError):
        source_line_number = 1
    if source_line_number < 1:
        source_line_number = 1
    kpi_data["source_line_number"] = source_line_number

    file_path = kpi_data.get("file_path")
    full_code = None
    if file_path:
        p = Path(file_path)
        if not p.is_absolute():
            p = (ROOT_DIR / p).resolve()
        else:
            p = p.resolve()
        if p.exists() and p.is_file():
            try:
                full_code = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    if full_code is not None:
        raw_code = full_code
        anchor_line = source_line_number
    else:
        raw_code = kpi_data.get("code_context") or ""
        anchor_line = kpi_line_in_context

    _, ext = os.path.splitext(str(file_path).lower())
    if ext == ".py":
        scoped_context, start_idx = _extract_function_block(
            raw_code, anchor_line
        )
        kpi_data["code_context"] = scoped_context
        if anchor_line > 0:
            rel = anchor_line - start_idx
            kpi_data["context_line_number"] = rel if rel > 0 else 0
        else:
            kpi_data["context_line_number"] = 0
        programmatic_formula = generate_formula_from_code(scoped_context)
    else:
        kpi_data["code_context"] = raw_code
        programmatic_formula = generate_formula_from_code(raw_code)
    # Committee artifacts retain portable evidence references, not machine-local IDE URLs.
    kpi_data["has_source_link"] = False
    kpi_data["vscode_url"] = ""
    kpi_data["pycharm_url"] = ""
    if file_path:
        try:
            display_base = Path(kpi_data.get("source_root") or ROOT_DIR).expanduser().resolve()
            kpi_data["source_file_display"] = str(Path(file_path).expanduser().resolve().relative_to(display_base))
        except Exception:
            kpi_data["source_file_display"] = str(file_path)
    else:
        kpi_data["source_file_display"] = ""
    kpi_data["source_language_display"] = (kpi_data.get("language") or "unknown").upper()
    kpi_data["detection_kind_display"] = (
        str(kpi_data.get("detection_kind") or kpi_data.get("_kind") or "unspecified")
        .replace("_", " ")
        .title()
    )
    try:
        kpi_data["confidence_display"] = f"{float(kpi_data.get('confidence', 0)):.0f}%"
    except Exception:
        kpi_data["confidence_display"] = "0%"
    
    # PHASE 1: Add confidence level categorization (High/Medium/Low)
    try:
        conf = float(kpi_data.get("confidence", 0))
        if conf >= 85:
            kpi_data["confidence_level"] = "High"
        elif conf >= 65:
            kpi_data["confidence_level"] = "Medium"
        else:
            kpi_data["confidence_level"] = "Low"
    except Exception:
        kpi_data["confidence_level"] = "Low"
    kpi_data["code_hash"] = hashlib.md5(
        (kpi_data.get("code_context") or "").encode("utf-8")
    ).hexdigest()[:10]
    identity_source = " ".join(
        str(kpi_data.get(key) or "")
        for key in ("name", "file_path", "code_context", "source_file_display")
    )
    identity_match = re.search(r"\bKPI[-_\s]?\d+\b", identity_source, re.I)
    if identity_match:
        kpi_data["kpi_identity_display"] = (
            identity_match.group(0).replace(" ", "").replace("_", "-").upper()
        )
    else:
        kpi_data["kpi_identity_display"] = f"KPI-{kpi_data['code_hash'].upper()}"
    from governance_patch import evaluate_all_conflicts
    governance = kpi_data.setdefault("governance", {})
    inferred_accountable = governance.get("accountable") or ""
    gov_eval = evaluate_all_conflicts(kpi_data, details, inferred_accountable)

    # Merge conflicts
    existing_conflicts = governance.setdefault("conflicts", [])
    for c in gov_eval.get("conflicts", []):
        if c not in existing_conflicts:
            existing_conflicts.append(c)

    # Merge audit notes
    existing_audit_notes = governance.setdefault("audit_notes", [])
    for n in gov_eval.get("audit_notes", []):
        if n not in existing_audit_notes:
            existing_audit_notes.append(n)

    # Merge compliance alarms
    existing_alarms = kpi_data.setdefault("compliance_alarms", [])
    for alarm in gov_eval.get("compliance_alarms", []):
        if alarm not in existing_alarms:
            existing_alarms.append(alarm)

    kpi_data["governance_responsible"] = governance.get("responsible") or ""
    kpi_data["governance_accountable"] = governance.get("accountable") or ""
    kpi_data["governance_consulted"] = governance.get("consulted") or ""
    kpi_data["governance_informed"] = governance.get("informed") or ""
    kpi_data["governance_basis"] = governance.get("basis") or ""
    kpi_data["governance_method"] = governance.get("method") or ""
    kpi_data["governance_confidence"] = governance.get("confidence") or ""

    # PHASE 1: Add governance status (Validated/Needs Review/Flagged)
    conflicts = governance.setdefault("conflicts", [])
    audit_notes = governance.setdefault("audit_notes", [])
    compliance_alarms = kpi_data.setdefault("compliance_alarms", [])
    formula_desc = (
        details.get("formula_description")
        or details.get("business_formula")
        or ""
    )
    has_formula_declared = formula_desc and not any(
        m in formula_desc.upper()
        for m in ("UNDETERMINED", "NOT DECLARED", "NO EXPLICIT", "OWNER CONFIRMATION",
                  "CERTIFIED FORMULA STATEMENT NOT DECLARED")
    )
    if conflicts or audit_notes or compliance_alarms:
        kpi_data["governance_status"] = "Needs Review"
        kpi_data["governance_status_display"] = "Needs Review"
    elif kpi_data["governance_accountable"]:
        kpi_data["governance_status"] = "Validated"
        kpi_data["governance_status_display"] = "Validated"
    else:
        kpi_data["governance_status"] = "Needs Review"
        kpi_data["governance_status_display"] = "Needs Review"
    domain = re.sub(
        r"\s*(Data Owner|Owner|Team|Department)\s*$",
        "",
        kpi_data["governance_accountable"],
        flags=re.I,
    ).strip()
    kpi_data["governance_domain_display"] = domain or "Enterprise KPI"
    # Context and programmatic formula were loaded/computed early at the start of the function
    formula_description_raw = details.get("formula_description", "") or ""

    def _looks_like_formula(text: str) -> bool:
        if not isinstance(text, str):
            return False
        s = text.strip()
        if not s:
            return False
        if "derived directly from the code" in s.lower():
            return False
        return any(op in s for op in ("/", "*", "×", "÷", "+", "-")) or bool(
            re.search(
                r"(?i)\b(?:minus|plus|divided\s+by|multiplied\s+by|sum\s+of|count\s+of)\b",
                s,
            )
        )

    def _formula_html_quality(formula_html: str) -> int:
        s = formula_html or ""
        if not s or "See code context" in s:
            return 0
        score = 2
        weak_bits = (
            "Placeholder",
            "= 0.0",
            "Nullif",
            "\\text{Count}",
            "\\text{Cast}",
            "\\text{Date Difference}",
            "\\text{Number}",
            "\\text{Return}",
        )
        if any(bit in s for bit in weak_bits):
            score -= 1
        if "\\frac" in s or "\\times" in s:
            score += 1
        return score

    formula_mismatch = False
    formula_mismatch_reason = ""
    if _looks_like_formula(formula_description_raw):
        formula_from_description = generate_formula_from_code(
            f"{kpi_name or 'Result'} = {formula_description_raw}"
        )
        description_quality = _formula_html_quality(formula_from_description.get("formula_html", ""))
        programmatic_quality = _formula_html_quality((programmatic_formula or {}).get("formula_html", ""))
        description_ops = set(re.findall(r"[+\-*/×÷]", formula_description_raw))
        programmatic_html = (programmatic_formula or {}).get("formula_html", "")
        programmatic_ops = set()
        if "\\frac" in programmatic_html:
            programmatic_ops.add("/")
        if "\\times" in programmatic_html:
            programmatic_ops.add("*")
        if " - " in programmatic_html:
            programmatic_ops.add("-")
        if " + " in programmatic_html:
            programmatic_ops.add("+")
        source_operator_lines = []
        for raw_line in (kpi_data.get("code_context") or "").splitlines():
            source_line = raw_line.strip()
            if not source_line:
                continue
            if source_line.startswith(("--", "#", "//", "'", "*")):
                # Completely skip all comment lines to avoid business formula/comment operator pollution
                continue
            # Remove function/arrow type symbols to avoid false operator detection
            source_line = source_line.replace("->", " ").replace("=>", " ")
            source_operator_lines.append(source_line)
        source_ops = set(re.findall(r"[+\-*/×÷]", "\n".join(source_operator_lines)))
        source_ops_normalized = set()
        if {"÷", "/"} & source_ops:
            source_ops_normalized.add("/")
        if {"×", "*"} & source_ops:
            source_ops_normalized.add("*")
        if "-" in source_ops:
            source_ops_normalized.add("-")
        if "+" in source_ops:
            source_ops_normalized.add("+")
        evidence_ops = programmatic_ops | source_ops_normalized
        clear_business_formula = description_quality > 0 and bool(description_ops)
        desc_has_pm = bool({"-", "+"} & description_ops)
        desc_has_div = bool({"/", "÷"} & description_ops)
        desc_has_mul = bool({"*", "×"} & description_ops)
        ev_has_pm = bool({"-", "+"} & evidence_ops)
        ev_has_div = bool({"/", "÷"} & evidence_ops)
        ev_has_mul = bool({"*", "×"} & evidence_ops)
        formula_mismatch = clear_business_formula and (
            (desc_has_pm and not ev_has_pm) or
            (desc_has_div and not ev_has_div) or
            (desc_has_mul and not ev_has_mul)
        )
        if formula_mismatch:
            # Provide an ISO-22400 aligned conflict signal and clear administrative phrasing.
            formula_mismatch_reason = (
                "The operational logic defined by business documentation does not align "
                "with the certified implementation path."
            )
            # Add to governance conflicts
            formula_conflict = {
                "reason": "ISO Compliance & Governance Conflict: " + formula_mismatch_reason,
                "severity": "High",
                "type": "formula_mismatch"
            }
            governance = kpi_data.setdefault("governance", {})
            existing_conflicts = governance.setdefault("conflicts", [])
            if formula_conflict not in existing_conflicts:
                existing_conflicts.append(formula_conflict)
            kpi_data["governance_status"] = "Needs Review"
            kpi_data["governance_status_display"] = "Needs Review"
        try:
            # Some callers build kpi_data earlier; ensure the key exists for templates.
            kpi_data["governance_conflict"] = bool(formula_mismatch)
        except Exception:
            pass
        if description_quality >= programmatic_quality or formula_mismatch:
            programmatic_formula = formula_from_description
    # If a governance/formula mismatch was detected, label it explicitly as an
    # ISO compliance conflict in the human-readable reason so the UI can show a
    # clear administrative warning.
    if formula_mismatch:
        formula_mismatch_reason = "ISO Compliance & Governance Conflict: " + formula_mismatch_reason

    # Variable to store LaTeX formula HTML if detected
    latex_formula_html = None

    # Check for explicit LaTeX formula in kpi_data before processing programmatic formula
    explicit_formula = str(kpi_data.get("formula") or "").strip()
    if explicit_formula and _looks_like_latex_formula(explicit_formula):
        # Extract the KPI name from comments to use as the normalized LHS
        explicit_kpi_name = None
        kpi_match = re.search(
            r"(?im)^\s*(?:--|#|//|/\*+|\*)\s*KPI\s*:?\s*(?P<name>.+?)\s*(?:\*/)?\s*$",
            kpi_data.get("code_context") or "",
        )
        if kpi_match:
            explicit_kpi_name = kpi_match.group("name").strip()
        
        # If we have a KPI name, normalize it and replace the LHS in the explicit formula
        if explicit_kpi_name:
            # Replace the LHS in the explicit formula with the normalized version
            # Match \mathrm{...} at the start before = and replace it
            def replace_lhs(match: re.Match) -> str:
                return _math_label(explicit_kpi_name) + " ="
            explicit_formula = re.sub(r"^(\\mathrm\s*\{[^{}]+\})\s*=", replace_lhs, explicit_formula)
        
        explicit_formula = _normalize_latex_formula(explicit_formula)
        kpi_data["formula"] = explicit_formula
        latex_formula = _latex_formula_html(explicit_formula)
        latex_formula_html = latex_formula["formula_html"]
        programmatic_formula = latex_formula

    final_details = {
        "description_html": format_text_as_html_list(_executive_text(details.get("description", ""), "objective")),
        "objective_html": format_text_as_html_list(_executive_text(details.get("objective", ""), "objective")),
        "formula_description": escape(_executive_text(formula_description_raw, "formula")),
        "used_in_kpis_html": format_text_as_html_list(_executive_text(details.get("used_in_kpis", ""), "usage")),
        "input_measure_html": format_text_as_html_list(
            _executive_text(details.get("input_measure", ""), "inputs")
        ),
        "unit_of_measure": escape(_executive_text(details.get("unit_of_measure", ""), "unit")),
        "reporting_source": escape(_executive_text(details.get("reporting_source", ""), "lineage")),
        "comments": escape(_executive_text(details.get("comments", ""), "comments")),
        **(programmatic_formula or {}),
    }

    # Ensure specific formula LHS for any generic result label
    if "formula_html" in final_details:
        formula_html = final_details["formula_html"]
        generic_patterns = [
            r"\\mathrm\s*\{\s*Result\s*\}",
            r"\\mathrm\s*\{\s*Metric\s*\}",
            r"\\mathrm\s*\{\s*Value\s*\}",
            r"\\mathrm\s*\{\s*Output\s*\}",
            r"\\mathrm\s*\{\s*Comment\\,Formula\\,Is\\,Inferred\s*\}",
            r"\\mathrm\s*\{\s*Comment\s+Formula\s+Is\s+Inferred\s*\}",
        ]
        target_lhs = _math_label(kpi_display_name)
        for pattern in generic_patterns:
            math_block_match = re.search(r"\\\[\s*(.*?)\s*\\\]", formula_html)
            if math_block_match:
                inner_math = math_block_match.group(1)
                match = re.match(pattern + r"\s*(=|\\approx|\\le|\\ge|\\equiv)\s*(.*)", inner_math)
                if match:
                    op = match.group(1)
                    rest = match.group(2)
                    new_inner_math = f"{target_lhs} {op} {rest}"
                    final_details["formula_html"] = formula_html.replace(inner_math, new_inner_math)
                    break

    if final_details.get("formula_result_name") in ("Result", "Metric", "Value", "Output"):
        final_details["formula_result_name"] = _normalize_business_identifier(kpi_display_name)

    if "formula_description" in final_details:
        desc = final_details["formula_description"]
        desc = re.sub(r"\bResult\s*=\s*", f"{kpi_display_name} = ", desc, flags=re.I)
        final_details["formula_description"] = desc


    def _plain_text(value: str) -> str:
        text = _sanitize_text(value or "")
        text = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", text).strip()
        return text

    def _is_undetermined_text(value: str) -> bool:
        normalized = str(value or "").upper()
        return (
            "UNDETERMINED" in normalized
            or "LINEAGE UNDETERMINED" in normalized
            or "NOT DECLARED" in normalized
            or "NO EXPLICIT" in normalized
            or "OWNER CONFIRMATION" in normalized
        )

    def _first_sentence(value: str, fallback: str) -> str:
        text = _plain_text(value)
        if not text:
            return fallback
        match = re.search(r"^(.{25,220}?[.!?])(?:\s|$)", text)
        if match:
            return match.group(1).strip()
        return text[:220].rstrip(" ,;") + ("." if not text.endswith(".") else "")

    def _business_formula_sentence() -> str:
        formula_text = _plain_text(formula_description_raw)
        if formula_text and not _is_undetermined_text(formula_text):
            return formula_text[0].upper() + formula_text[1:]
        
        source_formula = str((programmatic_formula or {}).get("formula_expression") or "").strip()
        if source_formula:
            return source_formula
        
        explicit_formula = str(kpi_data.get("formula") or "").strip()
        if explicit_formula:
            # Check for LaTeX syntax (backslashes, common LaTeX keywords)
            if _looks_like_latex_formula(explicit_formula):
                return _normalize_latex_formula(explicit_formula)
            return explicit_formula
        
        return (
            f"{kpi_name or 'This KPI'} is calculated from the certified operational logic "
            "shown in the evidence block."
        )

    def _movement_language(name: str) -> tuple[str, str]:
        lowered = (name or "").lower()
        negative_terms = (
            "complaint",
            "churn",
            "loss",
            "cost",
            "emission",
            "error",
            "failure",
            "downtime",
            "defect",
        )
        positive_terms = (
            "yield",
            "efficiency",
            "availability",
            "purity",
            "recovery",
            "utilization",
            "conversion",
            "selectivity",
            "oee",
            "service factor",
        )
        if any(term in lowered for term in negative_terms):
            return (
                "Usually signals a higher burden, risk, or exception volume that should be reviewed by the accountable owner.",
                "Usually signals lower burden or improved control, provided the data capture process has not changed.",
            )
        if any(term in lowered for term in positive_terms):
            return (
                "Usually signals better operating performance, assuming the denominator and period filters are unchanged.",
                "Usually signals weaker performance or a possible data-quality issue that should be investigated.",
            )
        return (
            "Indicates a material change in the measured business condition and should be interpreted with the owner.",
            "Indicates a material change in the measured business condition and should be checked against source-data timing.",
        )

    def _evidence_snippet() -> str:
        lines = (kpi_data.get("code_context") or "").splitlines()
        if not lines:
            return "No source code context was captured for this KPI."
        anchor = int(kpi_data.get("context_line_number") or 1)
        if anchor <= 0:
            anchor = 1
        start = max(0, anchor - 3)
        end = min(len(lines), anchor + 4)
        numbered = []
        for offset, line in enumerate(lines[start:end], start=start + 1):
            numbered.append(f"{offset:>4} | {line}")
        return "\n".join(numbered)

    def _developer_tokens_from_source() -> list[str]:
        source = "\n".join(
            raw
            for raw in (kpi_data.get("code_context") or "").splitlines()
            if raw.strip()
            and not raw.strip().startswith(("#", "--", "//", "/*", "*", "'"))
        )
        tokens: list[str] = []
        seen = set()
        patterns = (
            r"\b[A-Z][A-Z0-9_]{2,}\b",
            r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(",
            r"\b[a-zA-Z_][a-zA-Z0-9_]*\b",
        )
        stop_words = {
            "KPI",
            "CREATE",
            "OR",
            "REPLACE",
            "PACKAGE",
            "FUNCTION",
            "RETURN",
            "NUMBER",
            "END",
            "SELECT",
            "FROM",
            "WHERE",
            "CAST",
            "NULLIF",
            "SUM",
            "COUNT",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
        }
        for pattern in patterns:
            for match in re.finditer(pattern, source):
                token = match.group(0).strip().rstrip("(").strip()
                if len(token) < 3 or token.upper() in stop_words:
                    continue
                if token not in seen:
                    seen.add(token)
                    tokens.append(token)
                if len(tokens) >= 24:
                    return tokens
        return tokens

    def _token_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _developer_label_for(business_label: str, developer_tokens: list[str]) -> str:
        business_key = _token_key(business_label)
        if not business_key:
            return UNMAPPED_DEVELOPER_LINEAGE

        def _format_mapping(token: str) -> str:
            lang = (kpi_data.get("language") or "").lower()
            if lang == "python":
                return f"VARIABLE: {token}"
            if lang in {"sql", "tsql", "plsql", "hana"}:
                return f"COLUMN: {token}"
            return f"SOURCE TOKEN: {token}"

        token_pairs = [
            (token, _token_key(token))
            for token in developer_tokens
            if _token_key(token)
        ]
        for token, token_key in token_pairs:
            if token_key == business_key:
                return _format_mapping(token)
        for token, token_key in sorted(token_pairs, key=lambda item: len(item[1]), reverse=True):
            if business_key in token_key:
                return _format_mapping(token)
        for token, token_key in sorted(token_pairs, key=lambda item: len(item[1]), reverse=True):
            if token_key in business_key:
                return _format_mapping(token)
        business_words = [w for w in re.findall(r"[a-z0-9]+", business_label.lower()) if len(w) > 2]
        for token, token_key in sorted(token_pairs, key=lambda item: len(item[1]), reverse=True):
            if business_words and any(word in token_key for word in business_words):
                return _format_mapping(token)
        return UNMAPPED_DEVELOPER_LINEAGE

    def _code_role_for_line(line: str) -> str:
        clean = line.strip().rstrip(";")
        if clean in {"/", "GO"}:
            return "Execution delimiter: separates or submits the database package statement."
        if re.search(r"(?i)\b(compute|computes|calculation|formula)\b", clean):
            return "Calculation hint: documents the business expression expected inside the KPI implementation."
        if clean.startswith(("--", "#", "//", "'")):
            return "KPI marker: tells LEAP this nearby code defines or documents a KPI."
        if re.search(r"(?i)\bCREATE\s+OR\s+REPLACE\s+PACKAGE\b", clean):
            return "Package boundary: declares the interface where this KPI routine is published."
        function_match = re.search(r"(?i)\bFUNCTION\s+([a-zA-Z_][a-zA-Z0-9_]*)", clean)
        if function_match:
            if re.search(r"(?i)\bRETURN\s+NUMBER\b", clean):
                return (
                    f"KPI function: {function_match.group(1)} exposes this metric; "
                    "RETURN NUMBER declares the KPI result as numeric output."
                )
            return f"KPI function: {function_match.group(1)} is the callable routine that exposes this metric."
        if re.search(r"(?i)\bRETURN\s+NUMBER\b", clean):
            return "Return contract: the KPI output is numeric and can be used in calculations, dashboards, or thresholds."
        if re.search(r"(?i)\bEND\b", clean):
            return "Scope boundary: closes the KPI package, function, or code block."
        if re.search(r"(?i)\bSELECT\b", clean):
            return "Query entry point: starts the data-selection logic used to calculate the KPI."
        if re.search(r"(?i)\bAS\s+[a-zA-Z_][a-zA-Z0-9_]*\b", clean):
            alias = re.search(r"(?i)\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", clean)
            alias_text = alias.group(1) if alias else "the KPI output"
            return f"Output alias: maps this expression to {alias_text} in the result set."
        if re.search(r"[+\-*/×÷]", clean):
            return "Calculation expression: combines source variables used by the formal formula."
        if re.search(r"(?i)\bFROM\b", clean):
            return "Source relation: identifies the table, view, or dataset read by the KPI."
        return "Source context: supports the KPI definition or execution boundary."

    def _developer_lineage_html() -> str:
        lines = [line for line in (kpi_data.get("code_context") or "").splitlines() if line.strip()]
        if not lines:
            return ""
        rows = []
        for idx, line in enumerate(lines[:10], start=1):
            clean = line.strip()
            if len(clean) > 120:
                clean = clean[:117].rstrip() + "..."
            rows.append(
                '<div class="leap-code-lineage-row">'
                f'<div class="leap-code-lineage-code">{escape(str(idx))} | {escape(clean)}</div>'
                f'<div class="leap-code-lineage-role">{escape(_code_role_for_line(clean))}</div>'
                "</div>"
            )
        return (
            '<div class="leap-code-lineage" hidden>'
            '<div class="leap-code-lineage-title">Developer Lineage Breakdown</div>'
            + "".join(rows)
            + "</div>"
        )

    def _display_formula_symbol(token: str) -> str:
        mapping = {
            "*": "×",
            "×": "×",
            "/": "÷",
            "÷": "÷",
            "+": "+",
            "-": "-",
            "(": "(",
            ")": ")",
        }
        return mapping.get(token, token)

    def _business_label_for_code_token(token: str) -> str:
        if re.fullmatch(r"\d+(?:\.\d+)?", token.strip()):
            return token.strip()
        cleaned = token.strip()
        cleaned = re.sub(r'_(?:tons|pct|percent|hours|tons_day|tons_per_day|c|celsius|variance|variance_pct|cost_ratio|variance_variance)$', '', cleaned, flags=re.I)
        cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned.replace("_", " ")).strip()
        lower = cleaned.lower()
        compact = _token_key(cleaned)
        if compact in {"totalco2kg", "totalco2e", "totalco2emitted", "totalco2eemitted"}:
            return "Total Generated CO2e Emitted"
        if compact in {"grossgenerationmw", "netexportedgridmw", "netpowerexportedtogrid"}:
            return "Net Power Exported to Grid"
        if compact in {"totalinvoiceamt", "totalinvoiceamount"}:
            return "Total Invoice Amount"
        if compact in {"frameworkcontractamt", "frameworkcontractamount"}:
            return "Framework Contract Amount"
        if compact in {"totalcrackedliquids"}:
            return "Total Cracked Liquids"
        if compact in {"pureethyleneweight"}:
            return "Pure Ethylene Weight"
        if compact in {"feedstockinputweight"}:
            return "Feedstock Input Weight"
        if "accounts receivable" in lower:
            return "Accounts Receivable Balance"
        if "sales revenue" in lower or lower == "revenue":
            return "Total Sales Revenue"
        if "cash receipt" in lower:
            return "Cash Receipt Date"
        if "delivery date" in lower:
            return "Delivery Date"
        words = []
        for w in cleaned.split():
            if w.lower() in {'pct', 'tons', 'per', 'day', 'c'}:
                continue
            words.append(w.capitalize())
        res = " ".join(words)
        special_mappings = {
            "Ethylene Produced": "Ethylene Produced",
            "Feedstock Input": "Feedstock Input",
            "Revenue": "Revenue",
            "Cost": "Cost",
            "Operating Time": "Operating Time",
            "Failure Count": "Failure Count",
            "Operating Hours": "Operating Time",
            "Number Of Failures": "Failure Count",
        }
        return special_mappings.get(res, res or token)

    def _math_symbol_for_token(token: str) -> str:
        cleaned = token.strip()
        compact = _token_key(cleaned)
        if compact == "accountsreceivable":
            return "AR"
        if compact == "salesrevenue":
            return "Revenue"
        if compact == "cashreceiptdate":
            return "Cash Receipt"
        if compact == "deliverydate":
            return "Delivery"
        if compact in {"totalco2kg", "totalco2e", "totalco2emitted", "totalco2eemitted"}:
            return "CO_2e"
        if compact in {"grossgenerationmw", "netexportedgridmw", "netpowerexportedtogrid"}:
            return "MWh"
        if compact in {"totalinvoiceamt", "totalinvoiceamount"}:
            return "Invoice"
        if compact in {"frameworkcontractamt", "frameworkcontractamount"}:
            return "Contract"
        if compact == "totalcrackedliquids":
            return "Liquids"
        if compact == "pureethyleneweight":
            return "Ethylene"
        if compact == "feedstockinputweight":
            return "Feedstock"
        if cleaned in {"*", "×"}:
            return "×"
        if cleaned in {"/", "÷"}:
            return "÷"
        return _display_formula_symbol(cleaned)

    def _operator_label(token: str) -> tuple[str, str, str]:
        if token in {"/", "÷"}:
            return "Divided By", "OPERATOR: /", "÷"
        if token in {"*", "×"}:
            return "Multiplied By", "OPERATOR: *", "×"
        if token == "-":
            return "Minus", "OPERATOR: -", "-"
        if token == "+":
            return "Plus", "OPERATOR: +", "+"
        if token == "(":
            return "Open Group", "GROUP: (", "("
        if token == ")":
            return "Close Group", "GROUP: )", ")"
        return _display_formula_symbol(token), f"OPERATOR: {token}", _display_formula_symbol(token)

    def _source_expression_for_annotation() -> str:
        formula_expr = str((programmatic_formula or {}).get("formula_expression") or "").strip()
        if formula_expr and not _looks_like_latex_formula(formula_expr):
            return formula_expr
        source = kpi_data.get("code_context") or ""
        select_match = re.search(
            r"(?is)\bSELECT\b\s*(?P<expr>.+?)\s+\bAS\b\s+[a-zA-Z_][a-zA-Z0-9_]*",
            source,
        )
        if select_match:
            return select_match.group("expr").strip()
        return_matches = list(re.finditer(r"(?im)\breturn\b\s+(?P<expr>[^;\r\n]+)", source))
        if return_matches:
            return_matches.sort(
                key=lambda m: (
                    bool(re.search(r"[+\-*/×÷]", m.group("expr"))),
                    len(m.group("expr")),
                ),
                reverse=True,
            )
            return return_matches[0].group("expr").strip()
        assign_match = re.search(
            r"(?im)\b[a-zA-Z_][a-zA-Z0-9_]*\s*[:=]\s*(?P<expr>[^;\r\n]+)",
            source,
        )
        if assign_match:
            return assign_match.group("expr").strip()
        return ""

    def _fallback_annotation_expression() -> str:
        candidates = [
            str((programmatic_formula or {}).get("formula_expression") or "").strip(),
            str(kpi_data.get("formula") or "").strip(),
            _source_expression_for_annotation(),
            _plain_text(formula_description_raw),
        ]
        for candidate in candidates:
            if (
                candidate
                and not _is_undetermined_text(candidate)
                and not _looks_like_latex_formula(candidate)
            ):
                return candidate
        source = kpi_data.get("code_context") or ""
        math_lines: list[str] = []
        for raw in source.splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "--", "//", "/*", "*", "'")):
                continue
            if re.search(r"[+\-*/×÷]", line):
                math_lines.append(line)
        if math_lines:
            math_lines.sort(key=lambda line: ("return" in line.lower(), "/" in line or "*" in line, len(line)), reverse=True)
            line = math_lines[0]
            return_match = re.search(r"(?im)\breturn\b\s+(?P<expr>[^;\r\n]+)", line)
            if return_match:
                return return_match.group("expr").strip()
            assign_match = re.search(r"(?im)\b[a-zA-Z_][a-zA-Z0-9_]*\s*[:=]\s*(?P<expr>[^;\r\n]+)", line)
            if assign_match:
                return assign_match.group("expr").strip()
            return line
        function_match = re.search(r"(?im)\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
        if function_match:
            return function_match.group(1)
        sql_alias = re.search(r"(?is)\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\b", source)
        if sql_alias:
            return sql_alias.group(1)
        return kpi_display_name or kpi_name or kpi_data.get("name") or "Result"

    def _formula_rhs_for_annotation(expression: str) -> str:
        """
        Annotation nodes explain operands and operators, so they should use the
        calculation expression only. Human-certified formulas often include a
        publication title on the left side, e.g.
        "Ethylene Yield % = (Ethylene Produced / Feedstock) * 100". Keeping the
        left side inside the token stream makes it render as a fake operand.
        """
        text = str(expression or "").strip()
        if not text:
            return ""
        if _looks_like_latex_formula(text):
            return text
        depth = 0
        for idx, ch in enumerate(text):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(depth - 1, 0)
            elif ch == "=" and depth == 0:
                rhs = text[idx + 1 :].strip()
                lhs = text[:idx].strip()
                if rhs and lhs and re.search(r"[+\-*/×÷]|\b(?:divided|multiplied|minus|plus)\b", rhs, re.I):
                    return rhs
        return text

    def _strip_annotation_units(expression: str) -> str:
        """
        Unit parentheticals describe operands, but they are not standalone
        operands in the annotated equation. Keep grouped math intact and remove
        only common unit labels such as "(tons)" or "(hours)".
        """
        unit_terms = (
            r"%|percent|percentage|tons?|tonnes?|kg|kilograms?|m3|kg/m3|"
            r"hours?|hrs?|days?|c|°c|celsius|usd|\$|dollars?|units?"
        )
        return re.sub(rf"\s*\(\s*(?:{unit_terms})\s*\)", "", str(expression or ""), flags=re.I)

    def _tokenize_formula_expression(expression: str) -> list[str]:
        expression = _strip_annotation_units(_formula_rhs_for_annotation(expression))
        expression = re.sub(
            r"(?is)\b(?:SUM|AVG|MIN|MAX)\s*\(\s*([^()]+?)\s*\)",
            r"\1",
            expression or "",
        )
        expression = re.sub(
            r"(?is)\bNULLIF\s*\(\s*([^,()]+?)\s*,\s*0(?:\.0)?\s*\)",
            r"\1",
            expression,
        )
        expression = re.sub(r"(?is)\breturn\b\s+", "", expression)
        expression = re.sub(r"(?is)\bAS\s+[A-Za-z_][A-Za-z0-9_]*\b.*$", "", expression)
        expression = re.sub(r"[;,]+$", "", expression.strip())
        return [
            re.sub(r"^[,\s]+|[,\s]+$", "", part.strip())
            for part in re.split(r"(\+|-|\*|/|×|÷|\(|\))", expression)
            if part and part.strip() and re.sub(r"^[,\s]+|[,\s]+$", "", part.strip())
        ]

    def _formula_node_html(
        business_label: str,
        developer_label: str,
        symbol: str,
        extra_class: str = "",
    ) -> str:
        token = _formula_node_token(business_label, developer_label, symbol, extra_class)
        return (
            f'<div class="leap-formula-node{escape(token["extra_class"], quote=True)}">'
            f'<span class="leap-math-lbl{" long-line" if token["long_label"] else ""}" '
            f'data-biz="{escape(token["business_label"], quote=True)}" '
            f'data-dev="{escape(token["developer_mapping"], quote=True)}">{escape(token["business_label"])}</span>'
            '<div class="leap-math-pointer"></div>'
            f'<span class="leap-math-render">{escape(token["math_symbol"])}</span>'
            "</div>"
        )

    def _formula_node_token(
        business_label: str,
        developer_label: str,
        symbol: str,
        extra_class: str = "",
    ) -> dict:
        business_label = _shorten_label(business_label, 56)
        developer_label = _shorten_label(developer_label, 56)
        symbol = _shorten_label(symbol, 24)
        return {
            "business_label": business_label,
            "developer_mapping": developer_label,
            "math_symbol": symbol,
            # Compatibility aliases for any downstream code that has not migrated.
            "developer_label": developer_label,
            "symbol": symbol,
            "extra_class": extra_class,
            "is_operator": "operator-node" in extra_class,
            "long_label": len(business_label) > 22 or len(developer_label) > 22,
        }

    def _formula_tokens_from_expression(expression: str, prefer_source_labels: bool = False) -> list[dict]:
        parts = _tokenize_formula_expression(expression)
        tokens: list[dict] = []
        idx = 0
        while idx < len(parts):
            part = parts[idx]
            if part in {"(", ")"}:
                idx += 1
                continue
            if part in {"+", "-", "/", "÷"}:
                business, developer, symbol = _operator_label(part)
                tokens.append(_formula_node_token(business, developer, symbol, " operator-node"))
                idx += 1
                continue
            if part in {"*", "×"}:
                next_part = parts[idx + 1] if idx + 1 < len(parts) else ""
                if re.fullmatch(r"\d+(?:\.\d+)?", next_part):
                    tokens.append(
                        _formula_node_token(
                            "Normalized Annual Days" if next_part == "365" else f"Scaled by {next_part}",
                            f"LITERAL: * {next_part}",
                            f"× {next_part}",
                            " operator-node",
                        )
                    )
                    idx += 2
                    continue
                business, developer, symbol = _operator_label(part)
                tokens.append(_formula_node_token(business, developer, symbol, " operator-node"))
                idx += 1
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?", part):
                tokens.append(_formula_node_token(part, f"LITERAL: {part}", part))
                idx += 1
                continue
            if prefer_source_labels:
                business_label = _business_label_for_code_token(part)
                mapping_kind = "VARIABLE" if (kpi_data.get("language") or "").lower() == "python" else "COLUMN"
                developer_label = f"{mapping_kind}: {part}"
                symbol = _math_symbol_for_token(part)
            else:
                developer_tokens = _developer_tokens_from_source()
                business_label = part
                developer_label = _developer_label_for(part, developer_tokens)
                symbol = _math_symbol_for_token(part)
            tokens.append(_formula_node_token(business_label, developer_label, symbol))
            idx += 1
        return tokens

    def _nodes_from_expression(expression: str, prefer_source_labels: bool = False) -> list[str]:
        return [
            _formula_node_html(
                token["business_label"],
                token["developer_label"],
                token["symbol"],
                token["extra_class"],
            )
            for token in _formula_tokens_from_expression(expression, prefer_source_labels)
        ]

    def _shorten_label(label: str, max_len: int = 34) -> str:
        text = re.sub(r"\s+", " ", label).strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rstrip() + "…"

    def _annotated_equation_html() -> str:
        tokens = _annotated_equation_tokens()
        if not tokens:
            return ""
        return (
            '<div class="leap-annotated-formula-wrapper leap-annotated-equation" data-perspective="business">'
            + "".join(
                _formula_node_html(
                    token["business_label"],
                    token["developer_label"],
                    token["symbol"],
                    token["extra_class"],
                )
                for token in tokens
            )
            + "</div>"
        )

    def _annotated_equation_tokens() -> list[dict]:
        formula_text = _plain_text(formula_description_raw)
        source_expr = _fallback_annotation_expression()
        formula_expr_for_tokens = _formula_rhs_for_annotation(formula_text)
        if _looks_like_latex_formula(formula_text):
            source_tokens = _formula_tokens_from_expression(source_expr, prefer_source_labels=True)
            if source_tokens:
                return source_tokens
        if not _looks_like_formula(formula_text):
            return _formula_tokens_from_expression(source_expr, prefer_source_labels=True)
        aggregate_match = re.match(
            r"(?is)^(?P<kind>sum|count|average)\s+of\s+(?:all\s+)?(?P<item>.+)$",
            formula_text,
        )
        if formula_mismatch:
            source_tokens = _formula_tokens_from_expression(source_expr, prefer_source_labels=True)
            if source_tokens:
                return source_tokens
        if aggregate_match:
            kind = aggregate_match.group("kind").title()
            item = aggregate_match.group("item").strip()
            developer_tokens = _developer_tokens_from_source()
            business_label = _shorten_label(item, 56)
            developer_label = _shorten_label(_developer_label_for(item, developer_tokens), 48)
            symbol = "Σ" if kind == "Sum" else ("avg" if kind == "Average" else "count")
            return [_formula_node_token(business_label, developer_label, symbol)]
        tokens = _formula_tokens_from_expression(formula_expr_for_tokens, prefer_source_labels=False)
        operand_count = sum(1 for token in tokens if not token.get("is_operator"))
        return tokens if operand_count >= 2 else []

    def _normalize_formula_tokens(tokens: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for raw in tokens or []:
            if not isinstance(raw, dict):
                continue
            business_label = str(raw.get("business_label") or "").strip()
            developer_mapping = str(
                raw.get("developer_mapping") or raw.get("developer_label") or ""
            ).strip()
            math_symbol = str(raw.get("math_symbol") or raw.get("symbol") or "").strip()
            if not business_label or not developer_mapping or not math_symbol:
                continue
            token = _formula_node_token(
                business_label,
                developer_mapping,
                math_symbol,
                str(raw.get("extra_class") or (" operator-node" if raw.get("is_operator") else "")),
            )
            token["business_label"] = business_label
            token["developer_mapping"] = developer_mapping
            token["developer_label"] = developer_mapping
            token["math_symbol"] = math_symbol
            token["symbol"] = math_symbol
            token["is_operator"] = bool(raw.get("is_operator")) or "OPERATOR:" in developer_mapping
            token["long_label"] = len(business_label) > 22 or len(developer_mapping) > 22
            normalized.append(token)
        if not normalized:
            fallback_expr = _fallback_annotation_expression()
            fallback_label = _business_label_for_code_token(fallback_expr) if fallback_expr else (kpi_name or "Result")
            fallback_symbol = _math_symbol_for_token(fallback_expr) if fallback_expr else "Result"
            developer_mapping = UNMAPPED_DEVELOPER_LINEAGE
            token = _formula_node_token(fallback_label, developer_mapping, fallback_symbol)
            token["business_label"] = fallback_label
            token["developer_mapping"] = developer_mapping
            token["developer_label"] = developer_mapping
            token["math_symbol"] = fallback_symbol
            token["symbol"] = fallback_symbol
            token["long_label"] = len(fallback_label) > 22 or len(developer_mapping) > 22
            normalized.append(token)
        return normalized

    movement_up, movement_down = _movement_language(kpi_display_name)
    plain_meaning = _first_sentence(
        _executive_text(details.get("description", ""), "objective"),
        f"{kpi_display_name or 'This KPI'} is a governed operational indicator calculated from certified implementation logic.",
    )
    objective_text = _executive_text(details.get("objective", ""), "objective")
    if _is_undetermined_text(objective_text):
        decision_support = objective_text
    else:
        decision_support = _first_sentence(
            objective_text,
            f"Supports review of {kpi_data['governance_domain_display'].lower()} performance, ownership, and follow-up actions.",
        )
    input_text = _plain_text(_executive_text(details.get("input_measure", ""), "inputs"))
    if not input_text:
        input_text = "Review the operational evidence to confirm the exact fields, filters, and tables used."
    owner_logic = (
        f"If this KPI trends up: {movement_up} "
        f"If it trends down: {movement_down} "
        f"Owner check: What changed in source data, business process, or KPI logic that explains movement in {kpi_display_name or 'this KPI'}?"
    )

    def _walkthrough_operational_intent() -> str:
        meaning = _plain_text(plain_meaning)
        if meaning:
            return (
                f"{meaning} LEAP frames this as an operational evidence signal for "
                f"{kpi_data['governance_domain_display'].lower()} decision-making."
            )
        return (
            f"This metric exposes a measurable operating condition so {kpi_data['governance_domain_display'].lower()} "
            "leaders can compare performance, detect drift, and assign follow-up ownership."
        )

    def _walkthrough_recipe_html() -> str:
        formula_unresolved = _is_undetermined_text(formula_description_raw)
        formula = _plain_text(_executive_text(formula_description_raw, "formula")) or _plain_text(final_details.get("formula_description", ""))
        source = kpi_data.get("source_file_display") or "the captured source file"
        language = kpi_data.get("source_language_display") or "SOURCE"
        formula_step = (
            "Second, because no certified formula statement is declared in implementation comments, "
            "LEAP presents the executable calculation evidence in the formal MathJax formula shown above."
            if formula_unresolved
            else f"Second, it presents the certified calculation expression ({formula or 'the captured implementation expression'}) in the formal MathJax formula shown above."
        )
        steps = [
            f"First, LEAP certifies the KPI definition against {source} and classifies the implementation as {language} evidence.",
            formula_step,
            "Finally, it preserves the executable context and code fingerprint so future changes to the KPI logic can be identified.",
        ]
        return "<ol>" + "".join(f"<li>{escape(step)}</li>" for step in steps) + "</ol>"

    def _walkthrough_safeguards_html() -> str:
        code_context = kpi_data.get("code_context") or ""
        safeguards: list[tuple[str, str]] = []
        if re.search(r"(?is)\bNULLIF\s*\(", code_context):
            safeguards.append(
                (
                    "Zero-Division Guard",
                    "Implementation logic uses NULLIF so denominator values of zero do not create invalid ratio calculations.",
                )
            )
        elif re.search(r"(?is)\bif\s*\(.+==\s*0\)|\bif\s+.+==\s*0", code_context):
            safeguards.append(
                (
                    "Zero-Division Guard",
                    "Implementation logic checks for a zero denominator before returning the KPI value.",
                )
            )
        else:
            safeguards.append(
                (
                    "Implementation Traceability",
                    f"Executable evidence is locked to {kpi_data.get('source_file_display') or 'the captured implementation file'} at line {kpi_data.get('source_line_number', 1)}.",
                )
            )
        if formula_mismatch or has_any_conflict:
            if formula_mismatch:
                safeguard_reason = "LEAP identified that the documented business formula and implementation path disagree, so the KPI is explicitly flagged for owner review."
            else:
                first_c = kpi_data.get("governance", {}).get("conflicts", [{}])[0]
                safeguard_reason = first_c.get("reason") or "LEAP identified a governance conflict that requires owner review."
            safeguards.append(
                (
                    "Governance Conflict Flag",
                    safeguard_reason,
                )
            )
        else:
            safeguards.append(
                (
                    "Formula Consistency Check",
                    "The business formula and implementation evidence share compatible calculation structure based on LEAP's structured comparison.",
                )
            )
        safeguards.append(
            (
                "Change Detection",
                f"Code Fingerprint {kpi_data.get('code_hash', '')} records the current implementation so drift can be identified after the next workspace refresh.",
            )
        )
        if kpi_data.get("governance_accountable"):
            safeguards.append(
                (
                    "RACI Accountability",
                    f"{kpi_data['governance_accountable']} is assigned as accountable owner for rule confirmation and escalation.",
                )
            )
        return (
            '<div class="walkthrough-proof-list">'
            + "".join(
                '<div class="walkthrough-proof-item">'
                '<span class="walkthrough-check">OK</span>'
                f'<div><strong>{escape(title)}:</strong> {escape(body)}</div>'
                "</div>"
                for title, body in safeguards
            )
            + "</div>"
        )

    def _walkthrough_signoff() -> str:
        basis = kpi_data.get("governance_basis") or "local RACI governance rules"
        owner = kpi_data.get("governance_accountable") or "Domain Owner"
        consulted = kpi_data.get("governance_consulted") or "Domain SME"
        return (
            f"Business rules are aligned to {basis}. RACI Owner: {owner}. "
            f"Consulted reviewer: {consulted}. Current status: {review_state_label}."
        )

    review_body = "\n".join(
        [
            "Please review this governed KPI evidence package.",
            "",
            f"KPI: {kpi_display_name or 'KPI'}",
            f"KPI ID: {kpi_data.get('kpi_identity_display', '')}",
            f"Accountable owner: {kpi_data.get('governance_accountable', '')}",
            f"Consulted SME: {kpi_data.get('governance_consulted', '')}",
            f"Source: {kpi_data.get('source_file_display', '')}",
            f"Line: {kpi_data.get('source_line_number', '')}",
            "",
            "Review questions:",
            "- Does the business meaning match how the KPI is used?",
            "- Does the formula reflect the approved business rule?",
            "- Are the source fields, filters, and reporting period correct?",
            "- Should this KPI be marked Validated or Needs Review?",
        ]
    )
    formula_tokens = _normalize_formula_tokens(_annotated_equation_tokens())
    kpi_data["formula_tokens"] = formula_tokens

    formula_is_undetermined = _is_undetermined_text(formula_description_raw)
    governance_confidence_text = str(kpi_data.get("governance_confidence") or "").strip().lower()
    manual_override_approved = (
        str(details.get("_override_status") or "").strip().upper()
        == "APPROVED_BY_BUSINESS"
    )
    try:
        numeric_confidence = float(kpi_data.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        numeric_confidence = 0.0

    governance_payload = kpi_data.get("governance", {})
    has_any_conflict = bool(governance_payload.get("conflicts"))
    has_any_audit_note = bool(governance_payload.get("audit_notes"))
    has_any_compliance_alarm = bool(kpi_data.get("compliance_alarms"))
    if formula_mismatch or has_any_conflict or has_any_audit_note or has_any_compliance_alarm:
        review_state_label = "Needs Review"
        review_state_class = "state-needs-review"
        review_action_label = "Review Evidence Signals"
        if formula_mismatch:
            review_state_reason = formula_mismatch_reason
            review_action_label = "Review Logic Mismatch"
        elif has_any_conflict:
            first_c = governance_payload["conflicts"][0]
            review_state_reason = first_c.get("reason", "ISO Compliance & Governance Conflict detected.")
            review_action_label = "Review Governance Conflict"
        elif has_any_compliance_alarm:
            first_alarm = kpi_data["compliance_alarms"][0]
            review_state_reason = first_alarm.get("message", "Compliance alarm detected. Review required.")
            review_action_label = "Review Compliance Alarm"
        else:
            first_note = governance_payload["audit_notes"][0]
            if isinstance(first_note, dict):
                review_state_reason = first_note.get("reason", "Owner confirmation required.")
            else:
                review_state_reason = str(first_note)
            review_action_label = "Review Owner Confirmation"
    elif manual_override_approved:
        review_state_label = "Validated"
        review_state_class = "state-validated"
        review_action_label = "Review Approved Override"
        review_state_reason = (
            "This KPI uses a business-approved override from the LEAP AXIS sign-off ledger. "
            "The saved definition is applied before dossier rendering."
        )
    elif numeric_confidence < 75:
        review_state_label = "Needs Review"
        review_state_class = "state-needs-review"
        review_action_label = "Review Definition Evidence"
        review_state_reason = (
            "This governed metric requires owner confirmation because its confidence score does not yet meet certification criteria."
        )
    else:
        review_state_label = "Validated"
        review_state_class = "state-validated"
        review_action_label = "Review Certified Definition"
        review_state_reason = (
            "LEAP mapped the business definition, formula lineage, and governance metadata into a validated KPI dossier."
        )

    final_details.update(
        {
            "business_plain_meaning": escape(plain_meaning),
            "business_decision_support": escape(decision_support),
            "business_moves_up": escape(movement_up),
            "business_moves_down": escape(movement_down),
            "business_owner_logic": escape(owner_logic),
            "business_owner_question": escape(
                f"What changed in source data, business process, or KPI logic that explains movement in {kpi_display_name or 'this KPI'}?"
            ),
            "review_mailto": "mailto:?"
            + urlencode(
                {
                    "subject": f"LEAP KPI review requested: {kpi_display_name or 'KPI'}",
                    "body": review_body,
                }
            ),
            "review_body": escape(review_body),
            "review_body_textarea": escape(review_body).replace("\n", "&#10;"),
            "business_formula": escape(_business_formula_sentence()),
            "formula_tokens": formula_tokens,
            "annotated_equation_html": _annotated_equation_html(),
            "developer_lineage_html": _developer_lineage_html(),
            # Preserve rendered formula HTML; only replace it for explicit LaTeX.
            "formula_html": latex_formula_html or final_details.get("formula_html"),
            # Backwards-compatible flag used in some templates
            "has_governance_mismatch": bool(formula_mismatch) or has_any_conflict,
            # New ISO-focused conflict flag for templates and styling
            "iso_governance_conflict": bool(formula_mismatch) or has_any_conflict,
            # Human-readable reason (now prefixed with ISO label when applicable)
            "governance_mismatch_reason": escape(review_state_reason),
            "review_state_label": escape(review_state_label),
            "review_state_class": review_state_class,
            "review_action_label": escape(review_action_label),
            "review_state_reason": escape(review_state_reason),
            "walkthrough_operational_intent": escape(_walkthrough_operational_intent()),
            "walkthrough_recipe_html": _walkthrough_recipe_html(),
            "walkthrough_safeguards_html": _walkthrough_safeguards_html(),
            "walkthrough_signoff": escape(_walkthrough_signoff()),
            "evidence_snippet": escape(_evidence_snippet()),
        }
    )
    fields_to_check = [
        "description_html",
        "objective_html",
        "formula_description",
        "used_in_kpis_html",
        "input_measure_html",
        "unit_of_measure",
        "reporting_source",
        "comments",
    ]

    def _non_empty(val: str | None) -> bool:
        if not isinstance(val, str):
            return False
        s = val.strip()
        if len(s) <= 2:
            return False
        return not re.fullmatch(r"[\s\W_]*", s)

    filled = sum(1 for k in fields_to_check if _non_empty(final_details.get(k)))
    formula_html = final_details.get("formula_html") or ""
    formula_is_specific = bool(formula_html) and (
        "See code context" not in formula_html
    )
    filled_total = filled + (1 if formula_is_specific else 0)
    possible_total = len(fields_to_check) + 1
    extraction_rate_pct = round(100.0 * filled_total / possible_total, 1)
    error_rate_pct = round(100.0 - extraction_rate_pct, 1)
    validation_date_display = time.strftime("%Y-%m-%d")
    final_details["extraction_rate_pct"] = extraction_rate_pct
    final_details["error_rate_pct"] = error_rate_pct
    final_details["validation_date_display"] = validation_date_display
    kpi_data["extraction_rate_pct"] = extraction_rate_pct
    kpi_data["validation_date_display"] = validation_date_display

    def _fmt_seconds(s: float) -> str:
        s = max(0.0, float(s))
        if s < 60:
            return f"{s:.1f}s"
        m = int(s // 60)
        r = int(round(s - m * 60))
        return f"{m}m {r}s"

    render_time_seconds = time.perf_counter() - render_start
    total_kpi_time_seconds = (ai_time_seconds or 0.0) + render_time_seconds
    final_details["ai_time_seconds"] = round(ai_time_seconds or 0.0, 3)
    final_details["render_time_seconds"] = round(render_time_seconds, 3)
    final_details["total_kpi_time_seconds"] = round(total_kpi_time_seconds, 3)
    final_details["generation_time_display"] = validation_date_display
    explicit_formula = kpi_data.get("formula")
    if explicit_formula:
        # Check for LaTeX syntax (backslashes, keywords)
        if _looks_like_latex_formula(str(explicit_formula)):
            formula_res = _latex_formula_html(str(explicit_formula))
            if _formula_html_quality(formula_res.get("formula_html", "")) > _formula_html_quality(final_details.get("formula_html", "")):
                final_details["formula_html"] = formula_res.get("formula_html")
                final_details["formula_expression"] = formula_res.get("formula_expression", "")
        else:
            # Parse it using generate_formula_from_code
            formula_res = generate_formula_from_code(str(explicit_formula))
            if (
                formula_res
                and "See code context" not in formula_res.get("formula_html", "")
                and _formula_html_quality(formula_res.get("formula_html", "")) > _formula_html_quality(final_details.get("formula_html", ""))
            ):
                final_details["formula_html"] = formula_res.get("formula_html")
                final_details["formula_expression"] = formula_res.get("formula_expression", "")
            elif "See code context" in (final_details.get("formula_html") or ""):
                escaped_formula = str(explicit_formula).replace("%", r"\%")
                final_details["formula_html"] = f'<div class="math-equation">\\[ {escaped_formula} \\]</div>'
                governance = kpi_data.setdefault("governance", {})
                existing_notes = governance.setdefault("audit_notes", [])
                fallback_note = "Formula pipeline fell back to safe mode for review."
                if fallback_note not in existing_notes:
                    existing_notes.append(fallback_note)
    original_kpi_name = kpi_data.get("name") or ""
    safe_name = "".join(
        c for c in original_kpi_name if c.isalnum() or c in (" ", "_")
    ).rstrip()

    slug = safe_name.replace(" ", "_").lower()

    # If the slug is empty or generic, use the file stem
    if not slug or slug == "kpi":
        file_path = kpi_data.get("file_path")
        if file_path:
            file_stem = Path(file_path).stem.lower()
            if file_stem:
                slug = file_stem
        if not slug or slug == "kpi":
            slug = "kpi_dossier"

    base_filename = slug + ".rst"
    reserved_filenames = {"index.rst", "conf.rst", "genindex.rst", "search.rst"}
    filename = base_filename
    output_path = DOCS_SOURCE_DIR / filename
    if filename in reserved_filenames or output_path.exists():
        source_hint = str(kpi_data.get("file_path") or original_kpi_name or filename)
        digest = hashlib.md5(source_hint.encode("utf-8")).hexdigest()[:8]
        stem, suffix = os.path.splitext(base_filename)
        if base_filename in reserved_filenames:
            stem = f"kpi_{stem}"
        filename = f"{stem}_{digest}{suffix or '.rst'}"
        output_path = DOCS_SOURCE_DIR / filename
    content = template.render(kpi=kpi_data, details=final_details)
    if final_details.get("iso_governance_conflict") and final_details.get("governance_mismatch_reason"):
        content = content.replace(
            "The operational definition approved by the business does not align with the certified implementation path.",
            str(final_details["governance_mismatch_reason"]),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def _confidence_band(confidence: float) -> str:
    try:
        value = float(confidence)
    except Exception:
        value = 0.0
    if value >= 85:
        return "High"
    if value >= 65:
        return "Medium"
    return "Low"


def _slug_for_ref(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "kpi"


def create_discovery_report(
    kpis: list[dict],
    page_filenames: list[str],
    source_code_path: str,
    scan_stats: dict,
    ai_wall: float,
) -> str:
    from collections import Counter, defaultdict
    from html import escape

    report_name = "discovery_report.rst"
    report_path = DOCS_SOURCE_DIR / report_name
    paired = list(zip(kpis, page_filenames))
    total = len(kpis)
    avg_confidence = (
        sum(float(k.get("confidence", 0) or 0) for k in kpis) / total if total else 0.0
    )
    avg_quality = (
        sum(float(k.get("extraction_rate_pct", 0) or 0) for k in kpis) / total if total else 0.0
    )
    confidence_counts = Counter(_confidence_band(k.get("confidence", 0)) for k in kpis)
    language_counts = Counter((k.get("language") or "unknown").lower() for k in kpis)
    kind_counts = Counter(
        str(k.get("detection_kind") or k.get("_kind") or "unspecified")
        for k in kpis
    )
    domain_counts = Counter(
        k.get("governance_domain_display")
        or ((k.get("governance") or {}).get("domain"))
        or "Enterprise"
        for k in kpis
    )
    status_counts = Counter(
        k.get("governance_status") or "Validated"
        for k in kpis
    )
    accountable_counts = Counter(
        ((k.get("governance") or {}).get("accountable") or "Unassigned") for k in kpis
    )
    governance_method_counts = Counter(
        ((k.get("governance") or {}).get("method") or "Unspecified") for k in kpis
    )
    by_name = defaultdict(list)
    for k, page in paired:
        by_name[(k.get("display_name") or k.get("name") or "KPI").strip().lower()].append((k, page))
    duplicates = {
        name: entries for name, entries in by_name.items() if len(entries) > 1
    }

    def _card(label: str, value: str, caption: str = "", extra_class: str = "") -> str:
        badge_html = ""
        label_html = f'<span class="metric-indicator-label leap-card-label">{escape(label)}</span>'
        if "metric-review-items" in extra_class:
            badge_html = (
                '<div class="sidebar-status-badge state-needs-review" style="margin-bottom: 8px;">'
                '<span class="status-dot"></span>Needs Review'
                '</div>'
            )
            label_html = ""
        return (
            f'<div class="leap-metric-card metric-indicator-block {escape(extra_class)}">'
            f'{badge_html}'
            f'{label_html}'
            f'<span class="metric-indicator-value leap-card-value">{escape(value)}</span>'
            f'<span class="leap-card-caption">{escape(caption)}</span>'
            "</div>"
        )

    def _rows(counter: Counter, empty: str) -> str:
        if not counter:
            return f'<div class="sidebar-meta-row"><span>{escape(empty)}</span></div>'
        rows = []
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]).lower())):
            name_str = _business_label(str(name))
            if name_str in ["Needs Review", "Validated", "Draft", "Processing", "Deprecated", "Extracted"]:
                status_slug = name_str.lower().replace(" ", "-")
                label_html = (
                    f'<div class="sidebar-status-badge state-{status_slug}" style="margin-bottom: 0;">'
                    f'<span class="status-dot"></span>{escape(name_str)}'
                    f'</div>'
                )
            else:
                label_html = f'<span class="meta-label">{escape(name_str)}</span>'
            rows.append(
                '<div class="sidebar-meta-row" style="align-items: center;">'
                f'{label_html}'
                f'<span class="meta-value">{int(count):,}</span>'
                "</div>"
            )
        return "".join(rows)

    def _compact_rows(counter: Counter, empty: str, limit: int = 5) -> str:
        if not counter:
            return f'<div class="discovery-pill-row"><span>{escape(empty)}</span></div>'
        rows = []
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]).lower()))[:limit]:
            rows.append(
                '<div class="discovery-pill-row">'
                f'<span>{escape(_business_label(str(name)))}</span>'
                f'<strong>{int(count):,}</strong>'
                "</div>"
            )
        return "".join(rows)

    def source_display(k: dict) -> str:
        path = k.get("file_path") or ""
        if not path:
            return ""
        try:
            return str(Path(path).expanduser().resolve().relative_to(Path(source_code_path).expanduser().resolve()))
        except Exception:
            return str(path)

    inventory_rows = []
    for k, page in paired:
        stem = os.path.splitext(os.path.basename(page))[0]
        governance = k.get("governance") or {}
        status = k.get("governance_status") or "Validated"
        quality = float(k.get("extraction_rate_pct", 0) or 0)
        status_html = (
            '<div class="sidebar-status-badge state-needs-review" style="margin-bottom: 0; align-self: start;">'
            '<span class="status-dot"></span>Needs Review'
            '</div>'
            if status == "Needs Review"
            else '<div class="sidebar-status-badge state-validated" style="margin-bottom: 0; align-self: start; opacity: 0.72;">'
            '<span class="status-dot"></span>Validated'
            '</div>'
        )
        inventory_rows.append(
            '<a class="portfolio-dossier-row" href="'
            + escape(f"{stem}.html")
            + '">'
            '<div class="portfolio-dossier-name">'
            f'{status_html}'
            f'<strong>{escape(k.get("display_name") or k.get("name") or "Enterprise KPI")}</strong>'
            "</div>"
            '<div class="portfolio-dossier-meta">'
            f'<span>{float(k.get("confidence", 0) or 0):.0f}% confidence</span>'
            f'<span>{escape(k.get("governance_domain_display") or "Enterprise")}</span>'
            f'<span>{escape(governance.get("accountable") or "Unassigned")}</span>'
            f'<span>{quality:.1f}% readiness</span>'
            "</div>"
            "</a>"
        )

    duplicate_html = (
        "<p>No duplicate business metric names are active.</p>"
        if not duplicates
        else "".join(
            '<div class="sidebar-meta-row">'
            f'<span class="meta-label">{escape(entries[0][0].get("display_name") or entries[0][0].get("name") or "Enterprise KPI")}</span>'
            f'<span class="meta-value">{len(entries)} dossiers</span>'
            "</div>"
            for _, entries in sorted(duplicates.items(), key=lambda item: item[0])
        )
    )

    def _kpi_display_name(k: dict) -> str:
        return str(k.get("display_name") or k.get("name") or "Enterprise KPI")

    def _kpi_href(page: str) -> str:
        stem = os.path.splitext(os.path.basename(page))[0]
        return f"{stem}.html"

    def _objective_needs_confirmation(k: dict) -> bool:
        details = k.get("details") or {}
        objective = str(details.get("objective") or "").lower()
        return "not declared" in objective or "owner confirmation" in objective

    def _lineage_gap(k: dict) -> bool:
        details = k.get("details") or {}
        reporting_source = str(details.get("reporting_source") or "").lower()
        return "no explicit upstream system mapping" in reporting_source

    def _decision_rows(entries: list[tuple[dict, str]], empty: str, limit: int = 3) -> str:
        if not entries:
            return f'<p class="discovery-decision-empty">{escape(empty)}</p>'
        rows = []
        for k, page in entries[:limit]:
            governance = k.get("governance") or {}
            rows.append(
                f'<a class="discovery-decision-row" href="{escape(_kpi_href(page))}">'
                f'<strong>{escape(_kpi_display_name(k))}</strong>'
                '<span>'
                f'{float(k.get("confidence", 0) or 0):.0f}% confidence'
                f' · {escape(k.get("governance_domain_display") or "Enterprise")}'
                f' · {escape(governance.get("accountable") or "Unassigned")}'
                '</span>'
                '</a>'
            )
        return "".join(rows)

    owner_confirmation = [
        (k, page)
        for k, page in paired
        if _objective_needs_confirmation(k)
    ]
    lineage_gaps = [
        (k, page)
        for k, page in paired
        if _lineage_gap(k)
    ]
    readiness_watch = sorted(
        paired,
        key=lambda item: (
            float(item[0].get("extraction_rate_pct", 0) or 0),
            -float(item[0].get("confidence", 0) or 0),
            _kpi_display_name(item[0]).lower(),
        ),
    )
    confidence_leaders = sorted(
        paired,
        key=lambda item: (
            -float(item[0].get("confidence", 0) or 0),
            _kpi_display_name(item[0]).lower(),
        ),
    )
    domain_quality: dict[str, list[float]] = defaultdict(list)
    for k in kpis:
        domain = k.get("governance_domain_display") or "Enterprise"
        domain_quality[domain].append(float(k.get("extraction_rate_pct", 0) or 0))
    weakest_domain = "Enterprise"
    weakest_domain_score = avg_quality
    if domain_quality:
        weakest_domain, weakest_domain_score = min(
            (
                (domain, sum(scores) / len(scores))
                for domain, scores in domain_quality.items()
                if scores
            ),
            key=lambda item: (item[1], item[0].lower()),
        )

    decision_attention_count = sum(
        1
        for value in (
            len(owner_confirmation),
            len(lineage_gaps),
            len(duplicates),
            1 if weakest_domain_score < 90 else 0,
        )
        if value
    )

    html = f"""
<div class="enterprise-workspace-grid discovery-workspace-grid">
  <div class="enterprise-workspace-center">
    <section id="metric-portfolio" class="leap-metric-grid blueprint-header-stats">
      {_card("Enterprise KPIs", f"{total:,}", "enterprise KPI dossiers")}
      {_card("Average Confidence", f"{avg_confidence:.1f}%", "portfolio confidence")}
      {_card("Validated KPIs", f"{status_counts.get('Validated', 0):,}", "governed metrics")}
      {_card("Needs Review", f"{status_counts.get('Needs Review', 0):,}", "owner action required", "metric-review-items")}
    </section>

    <section id="confidence-summary" class="discovery-intelligence-band">
      <div class="discovery-band-heading">
        <div>
          <div class="micro-label">Portfolio Intelligence</div>
          <h2>Governed Metric Readiness</h2>
        </div>
        <p>{status_counts.get('Validated', 0):,} of {total:,} enterprise KPIs are validated for executive review.</p>
      </div>
      <div class="semantic-grid">
          {_card("High", f"{confidence_counts.get('High', 0):,}", "ready for executive use")}
          {_card("Medium", f"{confidence_counts.get('Medium', 0):,}", "owner confirmation recommended")}
          {_card("Low", f"{confidence_counts.get('Low', 0):,}", "requires business validation")}
          {_card("Definition Readiness", f"{avg_quality:.1f}%", "business definition completeness")}
      </div>
    </section>

    <section id="decision-cockpit" class="discovery-decision-cockpit">
      <div class="discovery-band-heading">
        <div>
          <div class="micro-label">Decision Cockpit</div>
          <h2>Portfolio Actions</h2>
        </div>
        <p>{decision_attention_count} attention categories require owner awareness before broad executive use.</p>
      </div>
      <div class="discovery-decision-grid">
        <article class="discovery-decision-card discovery-decision-card-primary">
          <div class="discovery-decision-kicker">{len(owner_confirmation):,} items</div>
          <h3>Owner Confirmation</h3>
          <p>Business objectives without declared source context should be confirmed by accountable owners.</p>
          <div class="discovery-decision-list">
            {_decision_rows(owner_confirmation, "No owner confirmation gaps found.")}
          </div>
        </article>
        <article class="discovery-decision-card">
          <div class="discovery-decision-kicker">{len(lineage_gaps):,} items</div>
          <h3>Lineage Gaps</h3>
          <p>Upstream system mapping is not explicit in implementation evidence.</p>
          <div class="discovery-decision-list">
            {_decision_rows(lineage_gaps, "No upstream lineage gaps found.")}
          </div>
        </article>
        <article class="discovery-decision-card">
          <div class="discovery-decision-kicker">{weakest_domain_score:.1f}% readiness</div>
          <h3>Weakest Domain</h3>
          <p>{escape(weakest_domain)} has the lowest average business definition readiness in the current portfolio.</p>
          <div class="discovery-decision-list">
            {_decision_rows(readiness_watch, "No readiness watch items found.")}
          </div>
        </article>
        <article class="discovery-decision-card">
          <div class="discovery-decision-kicker">Top confidence</div>
          <h3>Executive-Ready KPIs</h3>
          <p>Highest-confidence governed metrics ready for stakeholder review.</p>
          <div class="discovery-decision-list">
            {_decision_rows(confidence_leaders, "No confidence leaders found.")}
          </div>
        </article>
      </div>
    </section>

    <section id="domain-distribution" class="discovery-distribution-strip">
      <div class="discovery-distribution-panel">
        <h2>KPI Domains</h2>
        <div class="discovery-pill-grid">{_compact_rows(domain_counts, "No domains available", 6)}</div>
      </div>
      <div class="discovery-distribution-panel">
        <h2>Language Distribution</h2>
        <div class="discovery-pill-grid">{_compact_rows(language_counts, "No language metadata available", 6)}</div>
      </div>
    </section>

    <section id="kpi-inventory">
      <div class="dashboard-section-heading">
        <div>
          <div class="micro-label">Portfolio Inventory</div>
          <h2>Enterprise KPIs</h2>
        </div>
      </div>
      <div class="portfolio-dossier-list">
        {''.join(inventory_rows)}
      </div>
    </section>
  </div>

  <aside class="enterprise-workspace-rail">
    <section id="governance-summary" class="sidebar-card leap-card-secondary">
      <h2>Governance Status</h2>
      {_rows(status_counts, "No governance state available")}
    </section>
    <section class="sidebar-card leap-card-secondary">
      <h2>Ownership</h2>
      {_rows(accountable_counts, "No accountable owner assigned")}
    </section>
    <details class="evidence-lineage-panel">
      <summary>Portfolio Drill-Down</summary>
      <div class="evidence-detail-grid">
        <div>
          <div class="micro-label">Workspace Root</div>
          <strong class="font-mono">{escape(_package_display_path(source_code_path))}</strong>
        </div>
        <div>
          <div class="micro-label">Eligible Files</div>
          <strong>{int(scan_stats.get('files_scanned', 0)):,}</strong>
        </div>
        <div>
          <div class="micro-label">Business Definition Patterns</div>
          {_rows(kind_counts, "No definition pattern metadata available")}
        </div>
        <div>
          <div class="micro-label">Governance Assignment</div>
          {_rows(governance_method_counts, "No governance assignment metadata available")}
        </div>
        <div>
          <div class="micro-label">Name Collisions</div>
          {duplicate_html}
        </div>
      </div>
    </details>
  </aside>
</div>
"""

    lines = [
        "KPI Discovery Workspace",
        "=======================",
        "",
        ".. raw:: html",
        "",
    ]
    lines.extend(f"   {line}" if line else "" for line in html.strip().splitlines())

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_name


def create_raci_directory(kpis: list[dict]) -> str:
    from collections import Counter, defaultdict
    from html import escape

    directory_name = "raci_directory.rst"
    directory_path = DOCS_SOURCE_DIR / directory_name
    stakeholder_kpis: dict[tuple[str, str], set[str]] = defaultdict(set)
    stakeholder_roles: dict[tuple[str, str], set[str]] = defaultdict(set)

    role_map = [
        ("Responsible", "responsible"),
        ("Accountable", "accountable"),
        ("Consulted", "consulted"),
        ("Informed", "informed"),
    ]
    for kpi in kpis:
        governance = kpi.get("governance") or {}
        kpi_name = kpi.get("display_name") or kpi.get("name") or "KPI"
        for role_label, role_key in role_map:
            person = str(governance.get(role_key) or "").strip()
            if not person:
                continue
            key = (person, role_label)
            stakeholder_kpis[key].add(kpi_name)
            stakeholder_roles[key].add(role_label)

    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".") or "stakeholder"

    def _employee_id(name: str, role: str) -> str:
        digest = hashlib.md5(f"{name}:{role}".encode("utf-8")).hexdigest()[:6].upper()
        return f"LEAP-{digest}"

    def _email(name: str) -> str:
        return f"{_slug(name)}@enterprise.example"

    def _role_tier(role: str) -> str:
        return {
            "Accountable": "Decision Owner",
            "Responsible": "Execution Owner",
            "Consulted": "Subject Matter Reviewer",
            "Informed": "Executive Observer",
        }.get(role, "Governance Participant")

    rows = sorted(
        stakeholder_kpis.items(),
        key=lambda item: (item[0][1], item[0][0].lower()),
    )
    role_counts = Counter(role for (_name, role), _assigned in rows)
    stakeholder_count = len({name for (name, _role), _assigned in rows})
    assignment_count = sum(len(assigned) for (_key, assigned) in rows)
    governed_kpis = len(kpis)
    accountable_counts = Counter(
        str((kpi.get("governance") or {}).get("accountable") or "Unassigned").strip()
        or "Unassigned"
        for kpi in kpis
    )
    responsible_counts = Counter(
        str((kpi.get("governance") or {}).get("responsible") or "Unassigned").strip()
        or "Unassigned"
        for kpi in kpis
    )
    domain_owner_counts: dict[str, Counter[str]] = defaultdict(Counter)
    missing_accountable = []
    for kpi in kpis:
        governance = kpi.get("governance") or {}
        accountable = str(governance.get("accountable") or "").strip()
        domain = str(kpi.get("governance_domain_display") or "Enterprise")
        kpi_name = str(kpi.get("display_name") or kpi.get("name") or "Enterprise KPI")
        if accountable:
            domain_owner_counts[domain][accountable] += 1
        else:
            missing_accountable.append(kpi_name)

    top_accountable, top_accountable_count = (
        accountable_counts.most_common(1)[0] if accountable_counts else ("Unassigned", 0)
    )
    top_responsible, top_responsible_count = (
        responsible_counts.most_common(1)[0] if responsible_counts else ("Unassigned", 0)
    )
    concentration_pct = (
        (top_accountable_count / governed_kpis) * 100 if governed_kpis else 0.0
    )
    concentrated_domains = [
        (domain, owner, count)
        for domain, counter in domain_owner_counts.items()
        for owner, count in counter.most_common(1)
        if count > 1
    ]
    concentrated_domains.sort(key=lambda item: (-item[2], item[0].lower(), item[1].lower()))

    def _metric_card(label: str, value: str, caption: str) -> str:
        return (
            '<div class="leap-metric-card">'
            f'<div class="leap-card-label">{escape(label)}</div>'
            f'<div class="leap-card-value">{escape(value)}</div>'
            f'<div class="leap-card-caption">{escape(caption)}</div>'
            '</div>'
        )

    def _rows(counter: Counter[str], empty: str) -> str:
        if not counter:
            return f'<p class="text-metadata">{escape(empty)}</p>'
        return "".join(
            '<div class="sidebar-meta-row">'
            f'<span class="meta-label">{escape(str(name))}</span>'
            f'<span class="meta-value">{int(count):,}</span>'
            '</div>'
            for name, count in counter.most_common()
        )

    def _role_badge_class(role: str) -> str:
        return {
            "Responsible": "raci-r",
            "Accountable": "raci-a",
            "Consulted": "raci-c",
            "Informed": "raci-i",
        }.get(role, "raci-i")

    def _risk_card(label: str, value: str, caption: str, state: str = "") -> str:
        state_class = f" {state}" if state else ""
        return (
            f'<article class="raci-risk-card{state_class}">'
            f'<span>{escape(label)}</span>'
            f'<strong>{escape(value)}</strong>'
            f'<p>{escape(caption)}</p>'
            "</article>"
        )

    def _risk_rows(items: list[tuple[str, str, int]], empty: str, limit: int = 4) -> str:
        if not items:
            return f'<p class="raci-risk-empty">{escape(empty)}</p>'
        return "".join(
            '<div class="raci-risk-row">'
            f'<span>{escape(domain)}</span>'
            f'<strong>{escape(owner)}</strong>'
            f'<em>{int(count):,} KPIs</em>'
            '</div>'
            for domain, owner, count in items[:limit]
        )

    role_priority = {"Accountable": 0, "Responsible": 1, "Consulted": 2, "Informed": 3}
    by_stakeholder: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"roles": set(), "kpis": set()})
    for (name, role), assigned in rows:
        by_stakeholder[name]["roles"].add(role)
        by_stakeholder[name]["kpis"].update(assigned)

    stakeholder_rows = []
    for name, summary in sorted(by_stakeholder.items(), key=lambda item: item[0].lower()):
        roles = sorted(summary["roles"], key=lambda role: role_priority.get(role, 99))
        assigned = sorted(summary["kpis"])
        primary_role = roles[0] if roles else "Informed"
        role_badges = "".join(
            f'<span class="raci-badge {_role_badge_class(role)}">{escape(role[:1])}</span>'
            for role in roles
        )
        assigned_preview = ", ".join(assigned[:4])
        if len(assigned) > 4:
            assigned_preview += f" + {len(assigned) - 4} more"
        stakeholder_rows.append(
            '<div class="raci-stakeholder-row">'
            '<div class="raci-stakeholder-person">'
            f'<strong>{escape(name)}</strong>'
            f'<span>{escape(_email(name))}</span>'
            "</div>"
            '<div class="raci-stakeholder-roles">'
            f'{role_badges}'
            f'<span>{escape(_role_tier(primary_role))}</span>'
            "</div>"
            '<div class="raci-stakeholder-kpis">'
            f'<span>{len(assigned):,} KPI assignments</span>'
            f'<strong>{escape(assigned_preview or "No KPI assigned")}</strong>'
            "</div>"
            '<div class="raci-stakeholder-id">'
            f'<code>{escape(_employee_id(name, primary_role))}</code>'
            "</div>"
            "</div>"
        )

    table_rows = []
    for (name, role), assigned in rows:
        badge_class = _role_badge_class(role)
        assigned_preview = ", ".join(sorted(assigned)[:5])
        if len(assigned) > 5:
            assigned_preview += f" + {len(assigned) - 5} more"
        table_rows.append(
            "<tr>"
            f"<td><strong>{escape(name)}</strong></td>"
            f"<td><code>{escape(_email(name))}</code></td>"
            f"<td><code>{escape(_employee_id(name, role))}</code></td>"
            f"<td>{escape(assigned_preview or 'No KPI assigned')}</td>"
            f'<td><span class="raci-badge {badge_class}">{escape(role[:1])}</span>{escape(_role_tier(role))}</td>'
            "</tr>"
        )

    html = f"""
<div class="enterprise-workspace-grid raci-workspace-grid">
  <div class="enterprise-workspace-center">
    <section class="leap-metric-grid blueprint-header-stats">
      {_metric_card("Stakeholders", f"{stakeholder_count:,}", "unique governance participants")}
      {_metric_card("Role Assignments", f"{len(rows):,}", "RACI tiers across stakeholders")}
      {_metric_card("KPI Assignments", f"{assignment_count:,}", "stakeholder-to-metric links")}
      {_metric_card("Governed KPIs", f"{governed_kpis:,}", "enterprise KPI dossiers")}
    </section>

    <section id="governance-risk-signals" class="raci-risk-panel">
      <div class="raci-panel-heading">
        <div>
          <div class="micro-label">Governance Intelligence</div>
          <h2>Accountability Risk Signals</h2>
        </div>
        <p>Role-level interpretation of ownership concentration and coverage across governed KPIs.</p>
      </div>
      <div class="raci-risk-grid">
        {_risk_card("Top Accountable Owner", str(top_accountable), f"{top_accountable_count:,} KPIs · {concentration_pct:.0f}% of portfolio", "is-primary")}
        {_risk_card("Top Responsible Team", str(top_responsible), f"{top_responsible_count:,} KPI execution assignments")}
        {_risk_card("Missing Accountable Owners", f"{len(missing_accountable):,}", "KPIs without an accountable decision owner", "is-warning" if missing_accountable else "")}
        {_risk_card("Concentrated Domains", f"{len(concentrated_domains):,}", "domains with repeated accountability concentration")}
      </div>
      <div class="raci-risk-breakdown">
        <h3>Domain Concentration</h3>
        {_risk_rows(concentrated_domains, "No material domain concentration detected.")}
      </div>
    </section>

    <section id="stakeholder-accountability" class="sidebar-card leap-card-secondary raci-directory-panel">
      <div class="raci-panel-heading">
        <div>
          <div class="micro-label">Governance Directory</div>
          <h2>Stakeholder Accountability Matrix</h2>
        </div>
      </div>
      <div class="raci-stakeholder-list">
        {''.join(stakeholder_rows)}
      </div>
      <details class="raci-technical-directory">
        <summary>Role Assignment Detail</summary>
      <div class="raci-directory-table-wrap">
        <table class="raci-directory-table">
          <thead>
            <tr>
              <th>Employee Name</th>
              <th>Corporate Email</th>
              <th>Employee ID No</th>
              <th>Assigned KPIs</th>
              <th>Role Tier</th>
            </tr>
          </thead>
          <tbody>
            {''.join(table_rows)}
          </tbody>
        </table>
      </div>
      </details>
    </section>
  </div>

  <aside class="enterprise-workspace-rail">
    <section class="sidebar-card leap-card-secondary">
      <h2>RACI Distribution</h2>
      {_rows(role_counts, "No RACI assignments available")}
    </section>
    <section class="sidebar-card leap-card-tertiary">
      <h2>Directory State</h2>
      <div class="sidebar-meta-row"><span class="meta-label">Source</span><span class="meta-value">Governance Rules</span></div>
      <div class="sidebar-meta-row"><span class="meta-label">Mode</span><span class="meta-value">Read Only</span></div>
      <div class="sidebar-meta-row"><span class="meta-label">Scope</span><span class="meta-value">KPI Portfolio</span></div>
    </section>
    <section class="sidebar-card leap-card-tertiary action-card">
      <h2>Actions</h2>
      <button class="sidebar-btn btn-primary" type="button" onclick="window.print()">Print Directory</button>
      <a class="sidebar-btn btn-secondary" href="index.html">Return to Workspace</a>
      <a class="sidebar-btn btn-secondary" href="discovery_report.html">Open Discovery Workspace</a>
    </section>
  </aside>
</div>
"""

    lines = [
        "RACI Stakeholder Directory",
        "==========================",
        "",
        ".. raw:: html",
        "",
    ]
    lines.extend(f"   {line}" if line else "" for line in html.strip().splitlines())
    directory_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return directory_name


def create_extraction_review(candidate_review: list[dict], source_code_path: str, scan_stats: dict) -> str:
    from html import escape

    review_name = "extraction_review.rst"
    review_path = DOCS_SOURCE_DIR / review_name
    total = len(candidate_review or [])

    def _row(item: dict) -> str:
        reason = str(item.get("reason") or "Candidate did not meet promotion gate.")
        recommendation = str(item.get("recommendation") or "Review source evidence.")
        source = str(item.get("file_path") or "")
        try:
            source_display = os.path.relpath(source, ROOT_DIR) if source else ""
        except Exception:
            source_display = source
        excerpt = str(item.get("code_context_excerpt") or "").strip()
        if len(excerpt) > 900:
            excerpt = excerpt[:900] + "\n..."
        return f"""
        <details class="sidebar-card leap-card-tertiary extraction-review-item">
          <summary>
            <h3>{escape(str(item.get("candidate_name") or "Unnamed candidate"))}</h3>
            <span class="sidebar-status-badge state-needs-review"><span class="status-dot"></span>Candidate Only</span>
          </summary>
          <div class="card-row"><span class="label">Detection:</span><span class="value">{escape(str(item.get("detection_kind") or "unspecified"))}</span></div>
          <div class="card-row"><span class="label">Language:</span><span class="value">{escape(str(item.get("language") or "unknown"))}</span></div>
          <div class="card-row"><span class="label">Source:</span><span class="value code-font">{escape(source_display)}</span></div>
          <div class="card-row"><span class="label">Line:</span><span class="value">{escape(str(item.get("file_line") or 1))}</span></div>
          <div class="review-signal-card signal-owner">
            <div class="signal-title">Why it was not promoted</div>
            <div class="signal-message">{escape(reason)}</div>
          </div>
          <div class="review-signal-card signal-technical">
            <div class="signal-title">Recommended action</div>
            <div class="signal-message">{escape(recommendation)}</div>
          </div>
          <pre class="font-mono">{escape(excerpt)}</pre>
        </details>
        """

    rows_html = "\n".join(_row(item) for item in (candidate_review or [])[:300])
    hidden_count = max(0, total - 300)
    hidden_note = (
        f"<p>{hidden_count:,} additional candidates omitted from this display limit.</p>"
        if hidden_count
        else ""
    )
    html = f"""
<div class="enterprise-workspace-grid dashboard-workspace-grid">
  <div class="enterprise-workspace-center">
    <section class="dashboard-executive-panel dashboard-executive-panel-primary">
      <div class="micro-label">Extraction Quality Gate</div>
      <h2>Candidate Review</h2>
      <p>LEAP scanned the selected workspace and promoted only candidates with sufficient KPI evidence into executive dossiers. Weak or ambiguous candidates remain visible here for source-owner review.</p>
      <div class="dashboard-readiness-row">
        <div class="leap-metric-card metric-indicator-block">
          <span class="metric-indicator-label leap-card-label">Quarantined Candidates</span>
          <span class="metric-indicator-value leap-card-value">{total:,}</span>
          <span class="leap-card-caption">not counted as Enterprise KPIs</span>
        </div>
        <div class="leap-metric-card metric-indicator-block">
          <span class="metric-indicator-label leap-card-label">Implementation Files</span>
          <span class="metric-indicator-value leap-card-value">{int(scan_stats.get("files_scanned", 0) or 0):,}</span>
          <span class="leap-card-caption">evaluated by extractor</span>
        </div>
      </div>
      <p class="leap-card-caption">Source scanned: {escape(_package_display_path(source_code_path))}</p>
    </section>
    <section class="dashboard-dossier-section">
      <div class="dashboard-section-heading">
        <div>
          <div class="micro-label">Candidate Quarantine</div>
          <h2>Extraction Review Items</h2>
        </div>
      </div>
      <div class="portfolio-dossier-list dashboard-recent-list">
        {rows_html or "<p>No quarantined candidates were produced by this scan.</p>"}
        {hidden_note}
      </div>
    </section>
  </div>
</div>
"""
    lines = [
        "Extraction Review",
        "=================",
        "",
        ".. raw:: html",
        "",
    ]
    lines.extend(f"   {line}" if line else "" for line in html.strip().splitlines())
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review_name


def update_index_rst(page_filenames, kpis: list[dict] | None = None):
    from collections import Counter
    from html import escape

    index_path = DOCS_SOURCE_DIR / "index.rst"
    title = "KPI Intelligence Workspace"
    audit_stems = []
    kpi_stems = []
    kpis = kpis or []
    for fname in page_filenames or []:
        if not fname:
            continue
        try:
            base = os.path.basename(str(fname))
            stem = os.path.splitext(base)[0]
            if not stem:
                continue
            if stem in {"discovery_report", "raci_directory", "extraction_review"}:
                audit_stems.append(stem)
            else:
                kpi_stems.append(stem)
        except Exception:
            continue

    total = len(kpis)
    avg_confidence = (
        sum(float(k.get("confidence", 0) or 0) for k in kpis) / total if total else 0.0
    )
    avg_quality = (
        sum(float(k.get("extraction_rate_pct", 0) or 0) for k in kpis) / total if total else 0.0
    )
    status_counts = Counter(
        k.get("governance_status") or "Validated"
        for k in kpis
    )
    domain_counts = Counter(
        k.get("governance_domain_display")
        or ((k.get("governance") or {}).get("domain"))
        or "Enterprise"
        for k in kpis
    )
    language_counts = Counter((k.get("language") or "unknown").upper() for k in kpis)
    owner_counts = Counter(
        ((k.get("governance") or {}).get("accountable") or "Unassigned") for k in kpis
    )
    missing_objective_count = sum(
        1
        for k in kpis
        if "objective not declared" in str((k.get("details") or {}).get("objective") or "").lower()
    )
    missing_lineage_count = sum(
        1
        for k in kpis
        if "upstream system mapping" in str((k.get("details") or {}).get("reporting_source") or "").lower()
    )
    normalized_name_count = sum(1 for k in kpis if k.get("name_was_normalized"))
    low_readiness_count = sum(float(k.get("extraction_rate_pct", 0) or 0) < 85 for k in kpis)

    attention_items = [
        ("Blocked KPIs", status_counts.get("Needs Review", 0), "governance conflicts requiring owner action"),
        ("Owner Confirmation", missing_objective_count, "business objective requires accountable-owner confirmation"),
        ("Lineage Gaps", missing_lineage_count, "upstream system mapping requires owner confirmation"),
        ("Naming Normalized", normalized_name_count, "technical names converted to business metric labels"),
        ("Readiness Watch", low_readiness_count, "definition readiness below executive threshold"),
    ]
    active_attention_categories = sum(1 for _, value, _ in attention_items if int(value or 0) > 0)

    def _attention_rows() -> str:
        rows = []
        for label, value, caption in attention_items:
            state = "clear" if int(value or 0) == 0 else "active"
            rows.append(
                f'<div class="dashboard-attention-row is-{state}">'
                f'<span class="dashboard-attention-count">{int(value or 0):,}</span>'
                '<div>'
                f'<strong>{escape(label)}</strong>'
                f'<span>{escape(caption)}</span>'
                '</div>'
                '</div>'
            )
        return "".join(rows)

    recent_rows = []
    for k, stem in list(zip(kpis, kpi_stems))[:6]:
        governance = k.get("governance") or {}
        status = k.get("governance_status") or "Validated"
        status_html = (
            '<div class="sidebar-status-badge state-needs-review" style="margin-bottom: 0; align-self: start;">'
            '<span class="status-dot"></span>Needs Review'
            '</div>'
            if status == "Needs Review"
            else '<div class="sidebar-status-badge state-validated" style="margin-bottom: 0; align-self: start; opacity: 0.72;">'
            '<span class="status-dot"></span>Validated'
            '</div>'
        )
        recent_rows.append(
            '<a class="portfolio-dossier-row dashboard-dossier-row" href="'
            + escape(f"{stem}.html")
            + '">'
            '<div class="portfolio-dossier-name">'
            f'{status_html}'
            f'<strong>{escape(k.get("display_name") or k.get("name") or "Enterprise KPI")}</strong>'
            "</div>"
            '<div class="portfolio-dossier-meta">'
            f'<span>{float(k.get("confidence", 0) or 0):.0f}% confidence</span>'
            f'<span>{escape(k.get("governance_domain_display") or "Enterprise")}</span>'
            f'<span>{escape(governance.get("accountable") or "Unassigned")}</span>'
            "</div>"
            "</a>"
        )

    def _card(label: str, value: str, caption: str = "", extra_class: str = "") -> str:
        badge_html = ""
        label_html = f'<span class="metric-indicator-label leap-card-label">{escape(label)}</span>'
        if "metric-review-items" in extra_class:
            badge_html = (
                '<div class="sidebar-status-badge state-needs-review" style="margin-bottom: 8px;">'
                '<span class="status-dot"></span>Needs Review'
                '</div>'
            )
            label_html = ""
        return (
            f'<div class="leap-metric-card metric-indicator-block {escape(extra_class)}">'
            f'{badge_html}'
            f'{label_html}'
            f'<span class="metric-indicator-value leap-card-value">{escape(value)}</span>'
            f'<span class="leap-card-caption">{escape(caption)}</span>'
            "</div>"
        )

    def _compact_rows(counter: Counter, empty: str, limit: int = 6) -> str:
        if not counter:
            return f'<div class="discovery-pill-row"><span>{escape(empty)}</span></div>'
        return "".join(
            '<div class="discovery-pill-row">'
            f'<span>{escape(_business_label(str(name)))}</span>'
            f'<strong>{int(count):,}</strong>'
            "</div>"
            for name, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]).lower()))[:limit]
        )

    html = f"""
<div class="enterprise-workspace-grid dashboard-workspace-grid">
  <div class="enterprise-workspace-center">
    <section class="leap-metric-grid blueprint-header-stats dashboard-kpi-row">
      {_card("Enterprise KPIs", f"{total:,}", "enterprise KPI portfolio")}
      {_card("Average Confidence", f"{avg_confidence:.1f}%", "formula and lineage confidence")}
      {_card("Validated KPIs", f"{status_counts.get('Validated', 0):,}", "governed metrics")}
      {_card("Needs Review", f"{status_counts.get('Needs Review', 0):,}", "owner action required", "metric-review-items")}
    </section>

    <section class="dashboard-executive-grid">
      <div class="dashboard-executive-panel dashboard-executive-panel-primary">
        <div>
          <div class="micro-label">Portfolio Command</div>
          <h2>Operational KPI Coverage</h2>
        </div>
        <div class="dashboard-executive-metric">
          <strong>{total:,}</strong>
          <span>enterprise KPIs across {len(domain_counts):,} business domains</span>
        </div>
        <div class="discovery-pill-grid">{_compact_rows(domain_counts, "No domain metadata available", 6)}</div>
      </div>
      <div class="dashboard-executive-panel">
        <div>
          <div class="micro-label">Definition Authority</div>
          <h2>Governance & Readiness</h2>
        </div>
        <div class="dashboard-readiness-row">
          {_card("Readiness", f"{avg_quality:.1f}%", "definition completeness")}
          {_card("Validated", f"{status_counts.get('Validated', 0):,}", "governed metrics")}
        </div>
        <div class="discovery-pill-grid">{_compact_rows(language_counts, "No language metadata available", 6)}</div>
      </div>
    </section>

    <section class="dashboard-attention-section">
      <div class="dashboard-section-heading">
        <div>
          <div class="micro-label">Executive Attention</div>
          <h2>Needs Attention</h2>
        </div>
        <p>{active_attention_categories:,} of {len(attention_items):,} attention categories require executive awareness or owner confirmation.</p>
      </div>
      <div class="dashboard-attention-grid">
        {_attention_rows()}
      </div>
    </section>

    <section class="dashboard-dossier-section">
      <div class="dashboard-section-heading">
        <div>
          <div class="micro-label">Recent Activity</div>
          <h2>Enterprise KPI Dossiers</h2>
        </div>
      </div>
      <div class="portfolio-dossier-list dashboard-recent-list">
        {''.join(recent_rows)}
      </div>
    </section>
  </div>
</div>
"""

    lines = [
        title,
        "=" * len(title),
        "",
        ".. raw:: html",
        "",
    ]
    lines.extend(f"   {line}" if line else "" for line in html.strip().splitlines())
    lines.extend(
        [
            "",
            ".. toctree::",
            "   :hidden:",
            "   :maxdepth: 1",
            "",
        ]
    )
    lines.extend(f"   {stem}" for stem in audit_stems + kpi_stems)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_bluebook(source_code_path: str, ground_truth_path: str = None):
    run_start = time.perf_counter()
    build_dir = DOCS_SOURCE_DIR / "_build"
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
        yield "Cleared previous workspace artifacts."
    for item in DOCS_SOURCE_DIR.glob("*.rst"):
        if item.is_file() and item.name != "index.rst":
            item.unlink()
    yield "Reset prior workspace pages."
    yield f"Reading enterprise metric sources in: {source_code_path}"
    kpis, scan_stats = find_kpis_in_directory(source_code_path, include_stats=True)
    files_scanned = int(scan_stats.get("files_scanned", 0))
    lines_analyzed = int(scan_stats.get("lines_analyzed", 0))
    skipped_files = int(scan_stats.get("skipped_binary_files", 0))
    filesystem_files = int(scan_stats.get("filesystem_files", 0))
    filesystem_dirs = int(scan_stats.get("filesystem_dirs", 0))
    filesystem_items = int(scan_stats.get("filesystem_items", 0))
    files_after_dir_exclusions = int(scan_stats.get("files_after_directory_exclusions", 0))
    yield (
        f"Metric inventory: {len(kpis)} governed business metrics "
        f"(all files: {filesystem_files}, eligible files: {files_after_dir_exclusions}, "
        f"implementation files: {files_scanned})"
    )
    candidate_review = scan_stats.get("candidate_review") or []
    if candidate_review:
        yield f"Extraction promotion gate: {len(candidate_review)} weak KPI-like candidates routed to Extraction Review."
    attach_governance(kpis, ROOT_DIR, DOCS_SOURCE_DIR)
    # Load full code context to prevent any truncation during details generation and analysis
    for k in kpis:
        file_path = k.get("file_path")
        if file_path:
            p = Path(file_path)
            if not p.is_absolute():
                p = (ROOT_DIR / p).resolve()
            else:
                p = p.resolve()
            if p.exists() and p.is_file():
                try:
                    k["code_context"] = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass
    _prepare_kpi_display_names(kpis)
    yield "Governance layer: assigned RACI ownership using local rules and overrides."
    definition_overrides = _load_definition_overrides()
    if definition_overrides:
        yield f"Definition override ledger: loaded {len(definition_overrides)} approved override entries."
    if not kpis:
        yield "No enterprise KPIs found in the specified directory."
        return
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            [str(TEMPLATE_DIR), str(DOCS_SOURCE_DIR / "_templates")]
        )
    )
    env.globals["pathto"] = lambda path, relative=False: path
    try:
        template = env.get_template("kpi_template.rst.j2")
    except Exception:
        template = env.from_string(
            "{{ kpi.display_name or kpi.name }}\n{{ '=' * ((kpi.display_name or kpi.name)|length) }}\n\n"
            ".. raw:: html\n\n   {{ details.formula_html|safe }}\n\n"
            ".. admonition:: Code Context\n   :class: dropdown\n\n"
            "   .. code-block:: text\n      :linenos:\n\n"
            "      {{ kpi.code_context | e }}\n"
        )

    def _trim_context(kpi: dict, max_lines: int = 120, around: int = 60) -> str:
        ctx = kpi.get("code_context", "")
        line_no = int(kpi.get("file_line") or 0)
        lines = ctx.splitlines()
        if not lines:
            return ctx
        if 1 <= line_no <= len(lines):
            start = max(0, line_no - around - 1)
            end = min(len(lines), line_no + around)
            return "\n".join(lines[start:end])
        return "\n".join(lines[:max_lines])

    def _ai_task(k):
        name = k.get("name") or "KPI"
        display_name = k.get("display_name") or _business_display_name(name)
        t0 = time.perf_counter()
        try:
            trimmed = _trim_context(k)
            if len(trimmed) > 6000:
                trimmed = trimmed[:3000] + "\n...\n" + trimmed[-3000:]
            details = generate_kpi_details(display_name, trimmed)
            details = _apply_definition_override(k, details, definition_overrides)
            ai_time = time.perf_counter() - t0
            return (k, details, ai_time, None)
        except Exception as e:
            display_name = k.get("display_name") or _business_display_name(name)
            fallback = {
                "description": f'Certified operational definition for "{display_name}". Source evidence confirms the calculation path; accountable ownership confirms business use.',
                "objective": PROFESSIONAL_UNCERTAINTY_TEXT["objective"],
                "formula_description": PROFESSIONAL_UNCERTAINTY_TEXT["formula"],
                "used_in_kpis": PROFESSIONAL_UNCERTAINTY_TEXT["usage"],
                "input_measure": PROFESSIONAL_UNCERTAINTY_TEXT["inputs"],
                "unit_of_measure": PROFESSIONAL_UNCERTAINTY_TEXT["unit"],
                "reporting_source": PROFESSIONAL_UNCERTAINTY_TEXT["lineage"],
                "comments": PROFESSIONAL_UNCERTAINTY_TEXT["comments"],
            }
            fallback = _apply_definition_override(k, fallback, definition_overrides)
            return (k, fallback, 0.0, e)

    max_workers = int(os.environ.get("KPI_AI_WORKERS", "4"))
    ai_enabled = _ai_engine_enabled()
    worker_context = _worker_context(ai_enabled, max_workers)
    timing_label = "AI enrichment latency" if ai_enabled else "Deterministic detail preparation latency"
    results = []
    yield f"Business definition phase: preparing {len(kpis)} governed metrics{worker_context}..."
    ai_phase_start = time.perf_counter()
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(_ai_task, k): k for k in kpis}
        for fut in as_completed(future_map):
            k, details, ai_time, err = fut.result()
            name = k.get("name") or "KPI"
            if err:
                yield f"Business definition preparation failed for '{name}': {err}"
            else:
                yield f"Business definition ready for '{name}' ({ai_time:.2f}s)."
            results.append((k, details, ai_time))
    ai_wall = time.perf_counter() - ai_phase_start
    page_files = []
    rendered_kpis = []
    for k, details, ai_time in results:
        name = k.get("name") or "KPI"
        try:
            k["source_root"] = source_code_path
            k["details"] = details
            page = create_rst_file(k, details, template, ai_time_seconds=ai_time)
            page_files.append(page)
            rendered_kpis.append(k)
            yield f"Prepared dossier for '{name}'."
        except Exception as e:
            yield f"Failed to prepare dossier for '{name}': {e}"
    if results:
        total_ai = sum(ai for _, _, ai in results)
        avg_ai = total_ai / len(results)
        avg_wall_per_kpi = ai_wall / len(results)
        yield f"Business definition phase wall time: {ai_wall:.2f}s for {len(results)} KPIs{worker_context}."
        yield f"{timing_label} (sum across KPIs): {total_ai:.2f}s; avg per KPI latency: {avg_ai:.2f}s; avg wall time per KPI (wall/num): {avg_wall_per_kpi:.2f}s"
    total_conf = sum(k.get("confidence", 0) for k in kpis)
    avg_conf = total_conf / len(kpis) if kpis else 0
    false_positives = None
    false_negatives = None
    if ground_truth_path and os.path.exists(ground_truth_path):
        try:
            with open(ground_truth_path, "r", encoding="utf-8") as f:
                ground_truth = set(line.strip() for line in f if line.strip())
            metric_names = {k.get("name") for k in kpis if k.get("name")}
            false_positives = len(metric_names - ground_truth)
            false_negatives = len(ground_truth - metric_names)
        except Exception as e:
            yield f"Warning: could not load benchmark set: {e}"
    yield "=" * 70
    yield "KPI PORTFOLIO SUMMARY"
    yield f"Workspace items inventoried: {filesystem_items:,}"
    yield f"Workspace files inventoried: {filesystem_files:,}"
    yield f"Workspace directories inventoried: {filesystem_dirs:,}"
    yield f"Eligible files after exclusions: {files_after_dir_exclusions:,}"
    yield f"Implementation files evaluated: {files_scanned:,}"
    yield f"Binary/image files ignored: {skipped_files:,}"
    yield f"Unsupported files ignored: {int(scan_stats.get('unsupported_files', 0)):,}"
    yield f"Non-metric routines ignored: {int(scan_stats.get('filtered_non_kpi_candidates', 0)):,}"
    yield f"Candidate review queue: {len(candidate_review):,}"
    yield f"Configured ignored files: {int(scan_stats.get('ignored_files', 0)):,}"
    yield f"Configured ignored directories: {int(scan_stats.get('ignored_dirs', 0)):,}"
    yield f"Implementation lines evaluated: {lines_analyzed:,}"
    yield f"Enterprise KPIs: {len(kpis)}"
    yield f"Governed metrics: {len(kpis)}"
    if false_positives is not None:
        yield f"Benchmark false positives: {false_positives}"
        yield f"Benchmark false negatives: {false_negatives}"
    yield f"Average confidence: {avg_conf:.1f}%"
    yield "=" * 70
    try:
        report_page = create_discovery_report(
            rendered_kpis,
            page_files,
            source_code_path,
            scan_stats,
            ai_wall,
        )
        raci_page = create_raci_directory(rendered_kpis)
        review_page = create_extraction_review(candidate_review, source_code_path, scan_stats)
        update_index_rst([report_page, raci_page, review_page] + page_files, rendered_kpis)
        yield f"Workspace navigation updated with discovery workspace, RACI directory, and {len(page_files)} KPI dossiers."
    except Exception as e:
        yield f"Failed to update index.rst: {e}"
    try:
        if os.environ.get("SKIP_SPHINX"):
            yield "Skipped workspace HTML build (SKIP_SPHINX set)."
        else:
            jobs = os.environ.get("SPHINX_JOBS", "auto")
            cp = subprocess.run(
                [
                    "sphinx-build",
                    "-E",
                    "-a",
                    "-j",
                    jobs,
                    "-b",
                    "html",
                    str(DOCS_SOURCE_DIR),
                    str(DOCS_SOURCE_DIR / "_build"),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if cp.returncode == 0:
                # Upstream Post-Processing: Structurally remove Sphinx's duplicate document headings
                build_dir = DOCS_SOURCE_DIR / "_build"
                import re
                # Match Sphinx-generated duplicate h1 headings containing a class="headerlink" anchor.
                # Use a lookahead assertion (?!<h1>) to ensure we do not cross other h1 tags.
                headerlink_pattern = re.compile(
                    r'<h1>(?:(?!<h1>).)*?<a class="headerlink"[^>]*>.*?</a></h1>',
                    re.DOTALL
                )
                processed_count = 0
                for html_file in build_dir.glob("**/*.html"):
                    if html_file.is_file():
                        content = html_file.read_text(encoding="utf-8")
                        new_content = headerlink_pattern.sub('', content)
                        if new_content != content:
                            html_file.write_text(new_content, encoding="utf-8")
                            processed_count += 1
                yield f"Workspace build successful. Structurally resolved duplicate headings on {processed_count} pages."
            else:
                err = (cp.stderr or b"").decode("utf-8", errors="ignore")
                yield f"Workspace build finished with code {cp.returncode}.\n{err[:500]}"
    except Exception as e:
        yield f"Workspace HTML build not run: {e}"
    total_wall = time.perf_counter() - run_start
    yield f"Total wall time: {total_wall:.2f}s"
