import json
import re
from pathlib import Path
from typing import Any, Dict, List
from governance_patch import evaluate_all_conflicts
from .paths import GOVERNANCE_OVERRIDES_PATH, GOVERNANCE_RULES_PATH


DEFAULT_RACI = {
    "responsible": "Data Engineering Team",
    "accountable": "Enterprise Data Owner",
    "consulted": "Domain Subject Matter Expert",
    "informed": "Business Stakeholders",
    "basis": "default governance rule",
    "confidence": "Low",
    "override_applied": False,
}


def _safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback


def load_governance_rules(root_dir: Path) -> Dict[str, Any]:
    data = _load_json(GOVERNANCE_RULES_PATH, {})
    if isinstance(data, dict):
        return data
    return {}


def load_governance_overrides(docs_dir: Path) -> Dict[str, Any]:
    data = _load_json(GOVERNANCE_OVERRIDES_PATH, {})
    if isinstance(data, dict):
        return data
    return {}


def _iter_rules(rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    path_rules = rules.get("path_rules", [])
    name_rules = rules.get("name_rules", [])
    combined = []
    if isinstance(path_rules, list):
        for rule in path_rules:
            if isinstance(rule, dict):
                combined.append({**rule, "_rule_scope": "source path"})
    if isinstance(name_rules, list):
        for rule in name_rules:
            if isinstance(rule, dict):
                combined.append({**rule, "_rule_scope": "KPI name"})
    return combined


def _match_rule(kpi: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    pattern = _safe_text(rule.get("match"))
    if not pattern:
        return False
    scope = rule.get("_rule_scope")
    if scope == "source path":
        haystack = _safe_text(kpi.get("file_path")).lower()
    elif scope == "KPI name":
        haystack = _safe_text(kpi.get("name")).lower()
    else:
        haystack = f"{_safe_text(kpi.get('name'))} {_safe_text(kpi.get('file_path'))}".lower()
    try:
        return bool(re.search(pattern, haystack, re.I))
    except re.error:
        return pattern.lower() in haystack


def _override_candidates(kpi: Dict[str, Any]) -> List[str]:
    candidates = []
    for key in ("code_hash", "name", "file_path", "source_file_display"):
        value = _safe_text(kpi.get(key))
        if value:
            candidates.append(value)
            candidates.append(value.lower())
    return candidates


def _find_override(kpi: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    if not overrides:
        return {}
    override_blocks = []
    for key in ("kpis", "by_name", "by_hash", "by_source"):
        block = overrides.get(key)
        if isinstance(block, dict):
            override_blocks.append(block)
    if not override_blocks:
        override_blocks.append(overrides)
    for block in override_blocks:
        for candidate in _override_candidates(kpi):
            override = block.get(candidate)
            if isinstance(override, dict):
                return override
    return {}


def infer_raci(
    kpi: Dict[str, Any],
    rules: Dict[str, Any],
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    raci = dict(DEFAULT_RACI)
    matched_rule = None
    for rule in _iter_rules(rules):
        if _match_rule(kpi, rule):
            matched_rule = rule
            for key in ("responsible", "accountable", "consulted", "informed"):
                if rule.get(key):
                    raci[key] = _safe_text(rule.get(key))
            raci["basis"] = f"inferred from {rule.get('_rule_scope', 'rule')}: {rule.get('label') or rule.get('match')}"
            raci["confidence"] = _safe_text(rule.get("confidence") or "Medium")
            break

    override = _find_override(kpi, overrides or {})
    if override:
        for key in ("responsible", "accountable", "consulted", "informed", "basis", "confidence"):
            if override.get(key):
                raci[key] = _safe_text(override.get(key))
        raci["override_applied"] = True
        if not override.get("basis"):
            raci["basis"] = "manual governance override"
        if not override.get("confidence"):
            raci["confidence"] = "High"

    if not matched_rule and not override:
        language = _safe_text(kpi.get("language")).upper() or "UNKNOWN"
        raci["basis"] = f"default rule; no path/name governance match ({language})"

    raci["method"] = "Manual override" if raci["override_applied"] else "Rule-based inference"

    # Phase 3: Dynamic Logic Alerts
    # NOTE: At this point in the pipeline kpi.get('details', {}) may be empty
    # because AI-generated details are attached later (in generate_bluebook).
    # evaluate_all_conflicts is therefore called a second time from create_rst_file
    # (in main.py) once details are available. Conflicts detected there are merged
    # directly into kpi["governance"]["conflicts"] before template rendering.
    # The call here still runs evaluate_logic / code-annotation checks that only
    # need kpi.code_context (BUG/TODO detection, ISO template matching).
    inferred_accountable = raci.get("accountable", "")
    evaluation = evaluate_all_conflicts(kpi, kpi.get('details', {}), inferred_accountable)
    conflicts = evaluation.get('conflicts', [])
    audit_notes = evaluation.get('audit_notes', [])

    # Alert system only triggers for High severity
    high_conflicts = [c for c in conflicts if c['severity'] == 'High']
    if high_conflicts:
        raci['conflicts'] = high_conflicts
        raci['conflict_severity'] = 'High'

    # Merge audit notes for the review queue
    raci['audit_notes'] = audit_notes + [c for c in conflicts if c['severity'] != 'High']
    kpi['compliance_alarms'] = evaluation.get('compliance_alarms', [])
    return raci


def attach_governance(
    kpis: List[Dict[str, Any]],
    root_dir: Path,
    docs_dir: Path,
) -> List[Dict[str, Any]]:
    rules = load_governance_rules(root_dir)
    overrides = load_governance_overrides(docs_dir)
    for kpi in kpis:
        kpi["governance"] = infer_raci(kpi, rules, overrides)
    return kpis
