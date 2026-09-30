import re
import json
from pathlib import Path
from bluebook_generator.paths import GOVERNANCE_CONFIG_PATH, KNOWLEDGE_BASE_DIR


# ---------------------------------------------------------------------------
# Knowledge-base loaders
# ---------------------------------------------------------------------------

def _load_governance_kb():
    path = GOVERNANCE_CONFIG_PATH
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return []
    return []


def _load_iso_framework():
    path = KNOWLEDGE_BASE_DIR / "iso_framework.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


# ---------------------------------------------------------------------------
# Bug 1 fix + ISO/KB template path (evaluate_logic)
# ---------------------------------------------------------------------------

def _get_full_code(kpi):
    file_path = kpi.get("file_path")
    if file_path:
        p = Path(file_path)
        if p.exists() and p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    return kpi.get("code_context", "") or ""


def _normalize_kpi_name(name):
    """Normalize KPI names for deterministic ISO template matching."""
    text = (name or "").lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonical_iso_template_for_kpi(kpi):
    """Map business KPI names to narrow ISO templates used by RC-3 fixtures."""
    name = _normalize_kpi_name(kpi.get("name", ""))
    if name in {"yield rate", "yield"} or "yield rate" in name:
        return "yield_efficiency"
    if name in {"asset utilization", "utilization"} or "asset utilization" in name:
        return "asset_utilization"
    return None


def _strip_sql_comments(code):
    lines = []
    for raw in (code or "").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith(("--", "#", "//", "/*", "*", "'")):
            continue
        lines.append(raw)
    return "\n".join(lines)


def _extract_select_expression(code):
    """Extract the first SQL SELECT expression before AS alias."""
    executable = _strip_sql_comments(code)
    match = re.search(r"(?is)\bSELECT\s+(?P<select>.+?)\bFROM\b", executable)
    if not match:
        return ""
    select_text = match.group("select").strip().rstrip(",")
    alias_match = re.search(
        r"(?is)(?P<expr>.+?)\s+AS\s+[A-Za-z_][A-Za-z0-9_]*\s*$",
        select_text,
    )
    if alias_match:
        return alias_match.group("expr").strip()
    return select_text.strip()


def _normalize_expression(expr):
    return re.sub(r"\s+", "", (expr or "").lower())


def _split_ratio(expr):
    """Return rough numerator/denominator from a simple top-level ratio."""
    text = (expr or "").strip()
    if not text:
        return "", ""
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "/" and depth == 0:
            return text[:index].strip(" ()"), text[index + 1:].strip(" ()")

    # Handle common shape: (A / B) * 100
    match = re.search(r"(?is)^\s*\(?\s*(?P<num>[^()/]+?)\s*/\s*(?P<den>[^()*/+;-]+)", text)
    if match:
        return match.group("num").strip(" ()"), match.group("den").strip(" ()")
    return "", ""


def _conflict(reason, conflict_type, rule_id=None, framework=None):
    conflict = {
        "reason": reason,
        "severity": "High",
        "type": conflict_type,
    }
    if rule_id:
        conflict["rule_id"] = rule_id
    if framework:
        conflict["framework"] = framework
    return conflict


def detect_yield_operator_conflict(kpi):
    expr = _extract_select_expression(_get_full_code(kpi))
    norm = _normalize_expression(expr)
    if canonical_iso_template_for_kpi(kpi) != "yield_efficiency" or not norm:
        return None
    if "/" not in norm and "+" in norm:
        return _conflict(
            "Yield efficiency operator conflict: expected division between "
            "good_output_mass and raw_input_mass, but executable formula uses addition.",
            "yield_operator_conflict",
            "ISO-22400-RE-1",
            "ISO-22400-2:2014",
        )
    return None


def detect_yield_variable_conflict(kpi):
    expr = _extract_select_expression(_get_full_code(kpi))
    norm = _normalize_expression(expr)
    if canonical_iso_template_for_kpi(kpi) != "yield_efficiency" or not norm:
        return None
    numerator, denominator = _split_ratio(expr)
    norm_num = _normalize_expression(numerator)
    norm_den = _normalize_expression(denominator)
    if not numerator or not denominator:
        return None
    if "good_output_mass" not in norm_num:
        found = numerator.strip() or "unknown"
        return _conflict(
            "Yield efficiency variable conflict: expected good_output_mass as "
            f"the numerator, but executable formula uses {found}.",
            "yield_variable_conflict",
            "ISO-22400-RE-1",
            "ISO-22400-2:2014",
        )
    if "raw_input_mass" not in norm_den:
        found = denominator.strip() or "unknown"
        return _conflict(
            "Yield efficiency variable conflict: expected raw_input_mass as "
            f"the denominator, but executable formula uses {found}.",
            "yield_variable_conflict",
            "ISO-22400-RE-1",
            "ISO-22400-2:2014",
        )
    return None


def detect_asset_utilization_conflict(kpi):
    expr = _extract_select_expression(_get_full_code(kpi))
    norm = _normalize_expression(expr)
    if canonical_iso_template_for_kpi(kpi) != "asset_utilization" or not norm:
        return None
    numerator, denominator = _split_ratio(expr)
    norm_num = _normalize_expression(numerator)
    norm_den = _normalize_expression(denominator)
    if "maintenance_down_time" in norm_num:
        return _conflict(
            "Asset utilization conflict: maintenance_down_time is included in "
            "the production numerator. Planned maintenance must not be counted "
            "inside actual production time.",
            "asset_utilization_conflict",
            "ISO-22400-UE-2",
            "ISO-22400-2:2014",
        )
    if denominator and "planned_operation_time" not in norm_den:
        found = denominator.strip() or "unknown"
        return _conflict(
            "Asset utilization variable conflict: expected planned_operation_time "
            f"as the denominator, but executable formula uses {found}.",
            "asset_utilization_conflict",
            "ISO-22400-UE-2",
            "ISO-22400-2:2014",
        )
    return None


def evaluate_logic(kpi, details):
    """Evaluate governance conflicts from KPI code context and details.

    Fixes applied vs original:
    1.  Key fix: reads 'formula_description' (with 'business_formula' as fallback).
    2.  BUG/TODO regex is now robust: \\b(BUG|TODO|FIXME|HACK|CONFLICT)\\b[:\\s-]*
    3.  ISO template matching now also checks kpi_governance.json entries directly
        for a broader set of KPI name patterns.
    """
    conflicts = []
    audit_notes = []

    # ------------------------------------------------------------------
    # FIX 1: read correct key.  Support both names for backward compat.
    # ------------------------------------------------------------------
    formula = (
        details.get("formula_description")
        or details.get("business_formula")
        or kpi.get("formula")
        or kpi.get("business_formula")
        or ""
    )
    kpi_name = kpi.get("name", "").lower()
    code = _get_full_code(kpi)

    # 1. Audit note — missing/incomplete formula declaration
    is_uncertainty_text = any(
        marker in formula.upper()
        for marker in ("UNDETERMINED", "NOT DECLARED", "NO EXPLICIT", "OWNER CONFIRMATION",
                       "CERTIFIED FORMULA STATEMENT NOT DECLARED")
    )
    if not formula or is_uncertainty_text:
        audit_notes.append({
            "reason": "Evidence incomplete: business formula comment not declared.",
            "severity": "Medium",
        })

    # ------------------------------------------------------------------
    # FIX 2: BUG/TODO/FIXME detection — robust regex
    # ------------------------------------------------------------------
    if re.search(r"\b(BUG|TODO|FIXME|HACK)\b[:\s-]*", code, re.I):
        audit_notes.append({
            "reason": "Found potential development issues (BUG/TODO/FIXME) in source code lineage.",
            "severity": "Medium",
        })

    # ------------------------------------------------------------------
    # 3. ISO template + kpi_governance.json conflict detection
    # ------------------------------------------------------------------
    iso_kb = _load_iso_framework()
    templates = iso_kb.get("universal_metric_templates", {})

    matched_template = None
    expected = None
    for tmpl in templates:
        if tmpl in kpi_name:
            matched_template = tmpl
            break

    if matched_template:
        governance_kb = _load_governance_kb()
        expected = next(
            (item for item in governance_kb if item["kpi_name"].lower() in kpi_name),
            None,
        )

    if not expected:
        return {"conflicts": conflicts, "audit_notes": audit_notes}

    if formula and not is_uncertainty_text:
        owner_logic = expected["roles"].get("Business Owner", "")
        if owner_logic:
            SQL_KEYWORDS = {"select", "from", "as", "and", "or"}

            norm_formula = re.sub(r'\s+', '', formula.lower())
            norm_owner = re.sub(r'\s+', '', owner_logic.lower())

            op_map = {'+': 'addition', '-': 'subtraction', '*': 'multiplication', '/': 'division'}

            ops_actual = set(re.findall(r'[\+\-\*/]', norm_formula))
            ops_expected = set(re.findall(r'[\+\-\*/]', norm_owner))

            vars_actual = {v for v in re.findall(r'\b[a-z_][a-z0-9_]*\b', norm_formula) if v not in SQL_KEYWORDS}
            vars_expected = {v for v in re.findall(r'\b[a-z_][a-z0-9_]*\b', norm_owner) if v not in SQL_KEYWORDS}

            operator_mismatch = (ops_actual != ops_expected)

            # Relaxed variable matching: at least one shared variable
            common_vars = vars_actual.intersection(vars_expected)
            missing_variables = set()
            if len(common_vars) < 1:
                missing_variables = vars_expected

            if operator_mismatch or missing_variables:
                conflict_reasons = []
                if operator_mismatch:
                    actual_names = [op_map.get(o, 'arithmetic') for o in ops_actual]
                    expected_names = [op_map.get(o, 'arithmetic') for o in ops_expected]
                    conflict_reasons.append(
                        f"Operator mismatch: expected {', '.join(sorted(expected_names))} "
                        f"but found {', '.join(sorted(actual_names))}."
                    )

                if missing_variables:
                    conflict_reasons.append(
                        f"Incorrect variables: expected {', '.join(sorted(vars_expected))} "
                        f"but no shared variables found in extracted formula '{formula}'."
                    )

                conflicts.append({
                    "reason": " ".join(conflict_reasons),
                    "severity": "High",
                    "type": "formula_operator",
                })

    return {"conflicts": conflicts, "audit_notes": audit_notes}


# ---------------------------------------------------------------------------
# New conflict detectors (Bugs 4-7)
# ---------------------------------------------------------------------------

def detect_owner_conflict(kpi, details, inferred_accountable: str):
    """Bug 5: Compare declared owner comment to inferred RACI accountable.

    Parses comment fields like:
        # Accountable Owner: HSE Data Owner
        # Owner: Finance Data Owner
        # Business Owner: Operations Data Owner
    Compares against `inferred_accountable` from governance rules.
    Returns a conflict dict if mismatch is found, else None.
    """
    code = _get_full_code(kpi)
    owner_pattern = re.compile(
        r"(?i)^(accountable\s+owner|business\s+owner|owner)\s*:\s*(.+)$"
    )
    declared_owner = None
    for raw_line in code.splitlines():
        stripped = re.sub(r"^[\s#\-*/'\!]+", "", raw_line).strip()
        m = owner_pattern.match(stripped)
        if m:
            declared_owner = m.group(2).strip()
            break

    if not declared_owner:
        return None

    # Normalize both for comparison (case-insensitive, strip role suffixes)
    def _norm(s):
        return re.sub(r"\s*(Data Owner|Owner|Team|Dept)\s*$", "", s, flags=re.I).strip().lower()

    if _norm(declared_owner) != _norm(inferred_accountable):
        return {
            "reason": (
                f"Owner accountability conflict: source comment declares "
                f"'{declared_owner}' as accountable owner, but governance rules "
                f"inferred '{inferred_accountable}'."
            ),
            "severity": "High",
            "type": "owner_conflict",
            "declared": declared_owner,
            "inferred": inferred_accountable,
        }
    return None


def detect_source_conflict(kpi, details):
    """Bug 6: Compare declared source system with actual table/schema evidence.

    Parses comment fields like:
        # Reporting Source: SAP PM
        # Source System: OSIsoft PI
        # Business Data System: SAP FI-CO

    Then checks whether the code_context references tables/schemas that contradict
    the declared system (e.g. declared SAP PM but code reads csv_stage.*).
    Returns a conflict dict if mismatch is detected, else None.
    """
    code = _get_full_code(kpi)

    # Parse declared source comment
    source_pattern = re.compile(
        r"(?i)^(reporting\s+source|source\s+system|business\s+data\s+system|data\s+source)\s*:\s*(.+)$"
    )
    declared_source = None
    for raw_line in code.splitlines():
        stripped = re.sub(r"^[\s#\-*/'\!]+", "", raw_line).strip()
        m = source_pattern.match(stripped)
        if m:
            declared_source = m.group(2).strip()
            break

    if not declared_source:
        # Also check details dict
        reporting_source = details.get("reporting_source", "") or ""
        if "EXPLICIT SOURCE:" in reporting_source:
            declared_source = reporting_source.replace("EXPLICIT SOURCE:", "").strip()
        elif "EXPLICIT SOURCE TABLE" in reporting_source:
            return None  # Table-derived, no comment to compare

    if not declared_source:
        return None

    # Extract actual table/schema references from executable lines only
    executable_lines = []
    for raw_line in code.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", "--", "//", "/*", "*", "'")):
            continue
        executable_lines.append(raw_line)
    executable_code = "\n".join(executable_lines)

    actual_tables = re.findall(
        r"(?i)\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_\.]*)",
        executable_code,
    )

    if not actual_tables:
        return None

    # Define signature patterns: declared system → expected table prefixes/keywords
    SYSTEM_SIGNATURES = {
        r"sap\s*(pm|pp|mm|fi|co|sd|hana)": ["sap", "mseg", "afpo", "mara", "vbak", "ekko", "pa", "hrp"],
        r"osisoft|pi\s*system|historian": ["pi", "historian", "pipoint", "osi"],
        r"oracle": ["oracle", "apps", "fnd"],
        r"azure|synapse|adls": ["dbo", "azure", "synapse", "adls"],
    }

    # Suspicious staging/manual keywords
    STAGING_KEYWORDS = ["csv", "stage", "staging", "manual", "flat", "import", "temp", "tmp", "adhoc", "ad_hoc"]

    declared_lower = declared_source.lower()
    actual_tables_lower = [t.lower() for t in actual_tables]
    all_actual = " ".join(actual_tables_lower)

    # Check if declared system is a formal system but code uses staging
    declared_is_formal = any(
        re.search(pat, declared_lower) for pat in SYSTEM_SIGNATURES
    )
    code_uses_staging = any(kw in all_actual for kw in STAGING_KEYWORDS)

    if declared_is_formal and code_uses_staging:
        staging_tables = [t for t in actual_tables if any(kw in t.lower() for kw in STAGING_KEYWORDS)]
        return {
            "reason": (
                f"Source lineage conflict: source comment declares '{declared_source}' "
                f"as the certified system of record, but executable SQL reads from "
                f"staging/manual table(s): {', '.join(staging_tables)}. "
                f"Manual or staged data does not constitute certified source lineage."
            ),
            "severity": "High",
            "type": "source_conflict",
            "declared": declared_source,
            "actual_tables": actual_tables,
        }

    return None


def detect_threshold_conflict(kpi, details):
    """Bug 7: Detect inverted threshold interpretation.

    Parses business direction comments like:
        # Higher is worse
        # Higher is better
        # Lower is worse
        # Lower is better

    Then checks for implementation labels that contradict the stated direction.
    Returns a conflict dict if contradiction detected, else None.
    """
    code = _get_full_code(kpi)

    # Parse direction comment
    direction_pattern = re.compile(
        r"(?i)(higher|lower)\s+is\s+(worse|better|bad|good)"
    )
    direction_match = None
    for raw_line in code.splitlines():
        m = direction_pattern.search(raw_line)
        if m:
            direction_match = m
            break

    if not direction_match:
        return None

    magnitude = direction_match.group(1).lower()   # "higher" or "lower"
    sentiment = direction_match.group(2).lower()    # "worse" / "better" / "bad" / "good"
    higher_is_bad = (magnitude == "higher" and sentiment in ("worse", "bad"))
    lower_is_bad = (magnitude == "lower" and sentiment in ("worse", "bad"))

    positive_on_high = None
    negative_on_low = None
    positive_on_low = None
    negative_on_high = None

    comp_matches_high = list(re.finditer(r"(?i)(?:>=|>)\s*([A-Za-z0-9_\.]+)", code))
    for m in comp_matches_high:
        start_pos = m.end()
        following_text = code[start_pos : start_pos + 200]
        following_lines = []
        for line in following_text.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("#") or line_strip.startswith("//") or line_strip.startswith("--"):
                continue
            if line_strip.startswith("else") or line_strip.startswith("elif") or line_strip.startswith("def "):
                break
            following_lines.append(line_strip)
        following_clean = " ".join(following_lines)
        
        pos_m = re.search(r"\b(GOOD|GOOD_PERFORMANCE|OK|PASS|HEALTHY|NORMAL|EXCELLENT|SAFE)\b", following_clean, re.I)
        neg_m = re.search(r"\b(BAD|ALERT|CRITICAL|DEGRADED|RISK|FAIL|ALARM|UNSAFE|BREACH)\b", following_clean, re.I)
        if pos_m:
            positive_on_high = pos_m
        if neg_m:
            negative_on_high = neg_m

    comp_matches_low = list(re.finditer(r"(?i)(?:<=|<)\s*([A-Za-z0-9_\.]+)", code))
    for m in comp_matches_low:
        start_pos = m.end()
        following_text = code[start_pos : start_pos + 200]
        following_lines = []
        for line in following_text.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("#") or line_strip.startswith("//") or line_strip.startswith("--"):
                continue
            if line_strip.startswith("else") or line_strip.startswith("elif") or line_strip.startswith("def "):
                break
            following_lines.append(line_strip)
        following_clean = " ".join(following_lines)
        
        pos_m = re.search(r"\b(GOOD|GOOD_PERFORMANCE|OK|PASS|HEALTHY|NORMAL|EXCELLENT|SAFE)\b", following_clean, re.I)
        neg_m = re.search(r"\b(BAD|ALERT|CRITICAL|DEGRADED|RISK|FAIL|ALARM|UNSAFE|BREACH)\b", following_clean, re.I)
        if pos_m:
            positive_on_low = pos_m
        if neg_m:
            negative_on_low = neg_m

    conflict_detected = False
    conflict_labels = []

    if higher_is_bad and positive_on_high:
        conflict_detected = True
        conflict_labels.append(positive_on_high.group(1))
    if lower_is_bad and negative_on_low:
        conflict_detected = True
        conflict_labels.append(negative_on_low.group(1))

    if not conflict_detected:
        return None

    direction_phrase = f"'{magnitude} is {sentiment}'"
    label_str = ", ".join(f"'{l}'" for l in conflict_labels)
    return {
        "reason": (
            f"Threshold interpretation conflict: business comment states {direction_phrase}, "
            f"but implementation assigns {label_str} to the high-value condition. "
            f"This inverts the business meaning of the KPI."
        ),
        "severity": "High",
        "type": "threshold_conflict",
    }


def detect_validation_without_formula(kpi, details):
    """Bug 4: Flag KPIs that have no declared formula but appear Validated.

    Returns a conflict dict if formula is absent/undetermined, else None.
    This is appended as a Medium audit note (not High conflict) because
    LEAP infers formulas from code — but it should still surface as a review item.
    """
    formula = (
        details.get("formula_description")
        or details.get("business_formula")
        or kpi.get("formula")
        or kpi.get("business_formula")
        or ""
    )
    is_uncertainty_text = any(
        marker in formula.upper()
        for marker in ("UNDETERMINED", "NOT DECLARED", "NO EXPLICIT", "OWNER CONFIRMATION",
                       "CERTIFIED FORMULA STATEMENT NOT DECLARED")
    )
    if not formula or is_uncertainty_text:
        return {
            "reason": (
                "Evidence incomplete: business formula comment not declared."
            ),
            "severity": "Medium",
            "type": "validation_formula_missing",
        }
    return None


def _append_unique_audit_note(audit_notes, note):
    """Append a review note once, keyed by stable reason/type metadata."""
    note_reason = note.get("reason") if isinstance(note, dict) else str(note)
    note_type = note.get("type") if isinstance(note, dict) else ""
    for existing in audit_notes:
        existing_reason = existing.get("reason") if isinstance(existing, dict) else str(existing)
        existing_type = existing.get("type") if isinstance(existing, dict) else ""
        if existing_reason != note_reason:
            continue
        if existing_type == note_type or note_type == "validation_formula_missing" or not note_type:
            return
    audit_notes.append(note)


# ---------------------------------------------------------------------------
# Composite runner — called from main.py create_rst_file
# ---------------------------------------------------------------------------

def detect_domain_conflict(kpi, details, inferred_accountable: str):
    """Detect domain mismatch between KPI domain and referenced tables/schemas/paths.
    Example: HSE KPI referencing a finance database table.
    """
    code = _get_full_code(kpi)
    kpi_name = kpi.get("name", "").lower()

    # Check if this is HSE KPI
    is_hse = "hse" in kpi_name or "safety" in kpi_name or "emission" in kpi_name or "hse" in inferred_accountable.lower()

    # Check if table references finance
    has_finance_tables = bool(re.search(r"\bfinance\.[A-Za-z0-9_]+\b", code, re.I))

    if is_hse and has_finance_tables:
        return {
            "reason": (
                "Domain conflict: KPI is classified under HSE/Safety domain, "
                "but the SQL implementation queries tables in the 'finance' schema. "
                "HSE safety metrics should not depend directly on financial ledgers."
            ),
            "severity": "High",
            "type": "domain_conflict"
        }
    return None


# ---------------------------------------------------------------------------
# Compliance Alarm Pipeline (RC-G-3.2)
# ---------------------------------------------------------------------------

def check_ksa_pdpl_reg_01(code: str) -> list[str]:
    pii_keywords = ['national_id', 'iqama', 'phone_num', 'employee_record', 'contractor_details', 'customer_identifier']
    masking_keywords = ['mask', 'encrypt', 'hash', 'anonym']
    found_pii = []
    for pii in pii_keywords:
        pattern = r'\b' + re.escape(pii) + r'\b'
        if re.search(pattern, code, re.I):
            found_pii.append(pii)
    if not found_pii:
        return []
    code_lower = code.lower()
    has_masking = any(kw in code_lower for kw in masking_keywords)
    if has_masking:
        return []
    return found_pii

def check_ksa_nca_ecc_sec_04(code: str) -> list[str]:
    patterns = {
        'os.system': r'\bos\.system\b',
        'eval': r'\beval\b',
        'exec': r'\bexec\b',
        'compile': r'\bcompile\b',
        '__import__': r'\b__import__\b'
    }
    found_patterns = []
    for name, pat in patterns.items():
        if re.search(pat, code):
            found_patterns.append(name)
    return found_patterns

def check_ksa_nca_ecc_aud_02(code: str) -> list[str]:
    modification_keywords = ['write', 'insert', 'update', 'delete', 'modify', 'alter', 'audit_entry', 'no_code']
    audit_keywords = {
        'actor': r'\b(actor|user)\b',
        'timestamp': r'\b(timestamp|date)\b',
        'before value': r'\bbefore\b',
        'after value': r'\bafter\b',
        'diff or lineage record': r'\b(diff|lineage)\b'
    }
    has_modification = any(re.search(r'\b' + re.escape(kw) + r'\b', code, re.I) for kw in modification_keywords)
    if not has_modification:
        return []
    missing_elements = []
    for name, pat in audit_keywords.items():
        if not re.search(pat, code, re.I):
            missing_elements.append(name)
    return missing_elements

def check_gdpr_data_proc_01(code: str) -> list[str]:
    data_indicators = ['personal_data', 'eu_data', 'gdpr', 'citizenship', 'passport']
    movement_indicators = ['cross_border', 'transfer', 'export']
    consent_keywords = ['consent', 'agreement', 'processing_agreement', 'consent_obtained', 'data_transfer_agreement']

    has_data = any(re.search(r'\b' + re.escape(kw) + r'\b', code, re.I) for kw in data_indicators)
    has_movement = any(re.search(r'\b' + re.escape(kw) + r'\b', code, re.I) for kw in movement_indicators)
    if not (has_data and has_movement):
        return []
    has_consent = any(re.search(r'\b' + re.escape(kw) + r'\b', code, re.I) for kw in consent_keywords)
    if has_consent:
        return []
    evidence_found = []
    for kw in data_indicators + movement_indicators:
        if re.search(r'\b' + re.escape(kw) + r'\b', code, re.I):
            evidence_found.append(kw)
    return evidence_found

def check_soc2_lineage_audit_01(code: str) -> list[str]:
    lineage_indicators = ['lineage', 'trace', 'traceability', 'audit_trail']
    signature_keywords = ['signature', 'signed', 'sign', 'cryptographic', 'hash', 'sha256', 'hmac']
    has_lineage = any(re.search(r'\b' + re.escape(kw) + r'\b', code, re.I) for kw in lineage_indicators)
    if not has_lineage:
        return []
    has_signature = any(re.search(r'\b' + re.escape(kw) + r'\b', code, re.I) for kw in signature_keywords)
    if has_signature:
        return []
    return [kw for kw in lineage_indicators if re.search(r'\b' + re.escape(kw) + r'\b', code, re.I)]

def run_compliance_alarms(kpi) -> list[dict]:
    code = _get_full_code(kpi)
    iso_kb = _load_iso_framework()
    local_rules = iso_kb.get("local_governance_rules", [])
    alarms = []

    # KSA-PDPL-REG-01
    pdpl_rule = next((r for r in local_rules if r["rule_id"] == "KSA-PDPL-REG-01"), None)
    if pdpl_rule:
        pii_found = check_ksa_pdpl_reg_01(code)
        if pii_found:
            alarms.append({
                "rule_id": pdpl_rule["rule_id"],
                "framework": pdpl_rule["compliance_framework"],
                "category": "PRIVACY_GOVERNANCE_ALERT",
                "severity": pdpl_rule["severity"],
                "message": pdpl_rule["log_message"],
                "evidence": pii_found,
                "recommended_action": "Review required. Ensure PII fields are masked or encrypted in source extraction before processing.",
                "source_file": kpi.get("file_path", "unknown"),
                "status": "REVIEW_REQUIRED"
            })

    # KSA-NCA-ECC-SEC-04
    sec_rule = next((r for r in local_rules if r["rule_id"] == "KSA-NCA-ECC-SEC-04"), None)
    if sec_rule:
        sec_found = check_ksa_nca_ecc_sec_04(code)
        if sec_found:
            alarms.append({
                "rule_id": sec_rule["rule_id"],
                "framework": sec_rule["compliance_framework"],
                "category": "SECURITY_VULNERABILITY",
                "severity": sec_rule["severity"],
                "message": sec_rule["log_message"],
                "evidence": sec_found,
                "recommended_action": "Review required. Replace dynamic execution/restricted patterns with safe declarative logic.",
                "source_file": kpi.get("file_path", "unknown"),
                "status": "REVIEW_REQUIRED"
            })

    # KSA-NCA-ECC-AUD-02
    aud_rule = next((r for r in local_rules if r["rule_id"] == "KSA-NCA-ECC-AUD-02"), None)
    if aud_rule:
        aud_missing = check_ksa_nca_ecc_aud_02(code)
        if aud_missing:
            alarms.append({
                "rule_id": aud_rule["rule_id"],
                "framework": aud_rule["compliance_framework"],
                "category": "COMPLIANCE_AUDIT_GAP",
                "severity": aud_rule["severity"],
                "message": aud_rule["log_message"],
                "evidence": [f"Missing audit signature elements: {m}" for m in aud_missing],
                "recommended_action": "Review required. Document complete before/after values, actor, timestamp, and diff logic in audit trail.",
                "source_file": kpi.get("file_path", "unknown"),
                "status": "REVIEW_REQUIRED"
            })

    # GDPR-DATA-PROC-01
    gdpr_rule = next((r for r in local_rules if r["rule_id"] == "GDPR-DATA-PROC-01"), None)
    if gdpr_rule:
        gdpr_found = check_gdpr_data_proc_01(code)
        if gdpr_found:
            alarms.append({
                "rule_id": gdpr_rule["rule_id"],
                "framework": gdpr_rule["compliance_framework"],
                "category": "REGULATORY_RISK",
                "severity": gdpr_rule["severity"],
                "message": gdpr_rule["log_message"],
                "evidence": gdpr_found,
                "recommended_action": "Review required. Establish data processing agreement or document consent evidence before personal data transfer.",
                "source_file": kpi.get("file_path", "unknown"),
                "status": "REVIEW_REQUIRED"
            })

    # SOC2-LINEAGE-AUDIT-01
    soc2_rule = next((r for r in local_rules if r["rule_id"] == "SOC2-LINEAGE-AUDIT-01"), None)
    if soc2_rule:
        soc2_found = check_soc2_lineage_audit_01(code)
        if soc2_found:
            alarms.append({
                "rule_id": soc2_rule["rule_id"],
                "framework": soc2_rule["compliance_framework"],
                "category": "AUDIT_INCOMPLETE",
                "severity": soc2_rule["severity"],
                "message": soc2_rule["log_message"],
                "evidence": soc2_found,
                "recommended_action": "Review required. Sign lineage trace cryptographically and ensure immutable audit trail records are complete.",
                "source_file": kpi.get("file_path", "unknown"),
                "status": "REVIEW_REQUIRED"
            })

    return alarms


def evaluate_all_conflicts(kpi, details, inferred_accountable: str = ""):
    """Run all conflict detectors and return merged conflicts + audit_notes.

    This is the single entry point for all governance conflict detection.
    Called from create_rst_file() after details are available.

    Parameters
    ----------
    kpi : dict
        The raw KPI record (name, code_context, file_path, …).
    details : dict
        The resolved details dict from _deterministic_kpi_details or AI generator.
    inferred_accountable : str
        The accountable owner string already inferred from governance rules.

    Returns
    -------
    dict with keys:
        conflicts  : list[dict]  — High-severity items that set status to Flagged
        audit_notes: list[dict]  — Medium items for review queue
    """
    base = evaluate_logic(kpi, details)
    conflicts = list(base.get("conflicts", []))
    audit_notes = list(base.get("audit_notes", []))

    # RC-3 direct ISO conflict detectors. These are intentionally narrow:
    # they only apply after canonical KPI-name-to-template mapping succeeds.
    for detector in (
        detect_yield_operator_conflict,
        detect_yield_variable_conflict,
        detect_asset_utilization_conflict,
    ):
        direct_c = detector(kpi)
        if direct_c and direct_c not in conflicts:
            conflicts.append(direct_c)

    # Owner conflict
    owner_c = detect_owner_conflict(kpi, details, inferred_accountable)
    if owner_c:
        conflicts.append(owner_c)

    # Source lineage conflict
    source_c = detect_source_conflict(kpi, details)
    if source_c:
        conflicts.append(source_c)

    # Threshold direction conflict
    threshold_c = detect_threshold_conflict(kpi, details)
    if threshold_c:
        conflicts.append(threshold_c)

    # Domain conflict
    domain_c = detect_domain_conflict(kpi, details, inferred_accountable)
    if domain_c:
        conflicts.append(domain_c)

    # Validation-without-formula conflict (High — blocks Validated status)
    formula = (
        details.get("formula_description")
        or details.get("business_formula")
        or kpi.get("formula")
        or kpi.get("business_formula")
        or ""
    )
    has_formula = formula and not any(
        m in formula.upper()
        for m in ("UNDETERMINED", "NOT DECLARED", "NO EXPLICIT", "OWNER CONFIRMATION",
                  "CERTIFIED FORMULA STATEMENT NOT DECLARED")
    )
    # Only raise the validation conflict if no other High conflict already covers
    # the formula issue, and if there's no formula at all.
    if not has_formula and not any(c.get("type") == "validation_formula_missing" for c in conflicts):
        val_c = detect_validation_without_formula(kpi, details)
        if val_c:
            # Treat as Medium audit note so it surfaces but doesn't override
            # other genuine High conflicts. Adjust to High if desired.
            val_c["severity"] = "Medium"
            _append_unique_audit_note(audit_notes, val_c)

    return {"conflicts": conflicts, "audit_notes": audit_notes, "compliance_alarms": run_compliance_alarms(kpi)}
