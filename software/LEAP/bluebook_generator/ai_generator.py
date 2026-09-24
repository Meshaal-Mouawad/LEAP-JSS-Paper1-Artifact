"""Compliance details for LEAP KPI dossiers.

By default, this module reports only facts that can be extracted from source
context and marks everything else as undetermined for owner review. An optional
OpenAI detail engine can be enabled explicitly with ``LEAP_ENABLE_AI=1`` and an
``OPENAI_API_KEY``. That optional path is treated as draft enrichment and never
overrides explicit source lineage.
"""

from __future__ import annotations

import re
import os
import json
from typing import Any, Dict, List

__all__ = ["generate_kpi_details"]

LINEAGE_UNDETERMINED = (
    "No upstream system mapping was identified in the implementation evidence."
)
PROFESSIONAL_UNCERTAINTY_TEXT = {
    "objective": "Business objective is not declared in the source evidence. Owner confirmation is required before executive use.",
    "formula_description": "Certified formula statement not declared in implementation comments. LEAP presents the executable calculation evidence for owner confirmation.",
    "used_in_kpis": "Business-process usage mapping is not declared in the source evidence.",
    "input_measure": "Explicit input-field list is not declared in the source evidence.",
    "unit_of_measure": "Unit of measure is not declared in the source evidence.",
    "comments": "Compliance mode preserved only implementation-grounded evidence; unresolved business context is routed to owner confirmation.",
}
DETAIL_KEYS = (
    "description",
    "objective",
    "formula_description",
    "used_in_kpis",
    "input_measure",
    "unit_of_measure",
    "reporting_source",
    "comments",
)


def _strip_comment_prefix(line: str) -> str:
    return re.sub(
        r"^\s*(?:#|--|//|/\*+|\*|'|REM\b)\s*",
        "",
        line or "",
        flags=re.I,
    ).strip(" */")


def _explicit_comment_fields(code_context: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    aliases = {
        "description": "description",
        "meaning": "description",
        "objective": "objective",
        "intent": "objective",
        "business objective": "objective",
        "formula": "formula_description",
        "business formula": "formula_description",
        "input": "input_measure",
        "inputs": "input_measure",
        "input measure": "input_measure",
        "unit": "unit_of_measure",
        "unit of measure": "unit_of_measure",
        "reporting source": "reporting_source",
        "data source": "reporting_source",
        "source": "reporting_source",
        "used in": "used_in_kpis",
        "dashboard": "used_in_kpis",
        "comments": "comments",
    }
    pattern = re.compile(
        r"(?i)^(description|meaning|objective|intent|business objective|formula|business formula|input|inputs|input measure|unit|unit of measure|reporting source|data source|source|used in|dashboard|comments)\s*:\s*(.+)$"
    )
    for raw in (code_context or "").splitlines():
        match = pattern.match(_strip_comment_prefix(raw))
        if not match:
            continue
        key = aliases.get(match.group(1).lower())
        value = match.group(2).strip()
        if key and value:
            fields.setdefault(key, value)
    return fields


def _source_parameters(code_context: str) -> List[str]:
    params: List[str] = []
    source = code_context or ""
    fn_match = re.search(
        r"(?im)\bdef\s+[A-Za-z_][A-Za-z0-9_]*\s*\((?P<args>[^)]*)\)",
        source,
    )
    if fn_match:
        for raw in fn_match.group("args").split(","):
            name = raw.split(":", 1)[0].split("=", 1)[0].strip()
            if name and name not in {"self", "cls", "app", "request", "session"}:
                params.append(name)
    for match in re.finditer(
        r"(?i)\b(?:SUM|AVG|COUNT|MIN|MAX|NULLIF)\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)",
        source,
    ):
        params.append(match.group(1))
    return _dedupe(params)[:12]


def _source_tables(code_context: str) -> List[str]:
    executable_lines = []
    for raw in (code_context or "").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith(("#", "--", "//", "/*", "*", "'")):
            continue
        executable_lines.append(raw)
    executable_source = "\n".join(executable_lines)
    tables = [
        match.group(1).strip('[]"')
        for match in re.finditer(
            r"(?is)\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_\.\[\]\"]*)",
            executable_source,
        )
    ]
    return _dedupe(tables)[:8]


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def _explicit_unit(kpi_name: str, fields: Dict[str, str]) -> str:
    if fields.get("unit_of_measure"):
        return fields["unit_of_measure"]
    lowered = (kpi_name or "").lower()
    if any(
        marker in lowered
        for marker in ["%", " pct", "_pct", "percent", "percentage", "rate"]
    ):
        return "%"
    if "ratio" in lowered:
        return "ratio"
    return PROFESSIONAL_UNCERTAINTY_TEXT["unit_of_measure"]


def _sql_implementation(code_context: str) -> str:
    """Attempt to reconstruct or extract an SQL representative of the KPI."""
    source = code_context or ""
    # 1. Look for existing SQL
    sql_match = re.search(r"(?is)\b(SELECT\s+.+?FROM\s+.+?)(?:;|\n\s*\n|\bWHERE\b|\bGROUP\b|\bORDER\b)", source)
    if sql_match:
        return sql_match.group(1).strip()
    # 2. Heuristic generation from tables/params
    tables = _source_tables(code_context)
    params = _source_parameters(code_context)
    if tables:
        fields = ", ".join(params) if params else "*"
        return f"SELECT {fields} FROM {tables[0]};"
    return "-- No SQL implementation could be automatically derived."

def _deterministic_kpi_details(kpi_name: str, code_context: str) -> Dict[str, Any]:
    """Return only source-grounded detail fields for the KPI template."""
    fields = _explicit_comment_fields(code_context)
    params = _source_parameters(code_context)
    tables = _source_tables(code_context)
    display_name = (kpi_name or "Unnamed KPI").replace("_", " ").strip()

    details = {
        "description": fields.get("description") or f"Certified operational definition for \"{display_name}\". Source evidence confirms the calculation path; accountable ownership confirms business use.",
        "objective": fields.get("objective") or PROFESSIONAL_UNCERTAINTY_TEXT["objective"],
        "formula_description": fields.get("formula_description") or PROFESSIONAL_UNCERTAINTY_TEXT["formula_description"],
        "used_in_kpis": fields.get("used_in_kpis") or PROFESSIONAL_UNCERTAINTY_TEXT["used_in_kpis"],
        "input_measure": fields.get("input_measure") or PROFESSIONAL_UNCERTAINTY_TEXT["input_measure"],
        "unit_of_measure": _explicit_unit(kpi_name, fields),
        "reporting_source": LINEAGE_UNDETERMINED,
        "comments": fields.get("comments") or PROFESSIONAL_UNCERTAINTY_TEXT["comments"],
        "suggested_sql": _sql_implementation(code_context)
    }

    if tables:
        details["reporting_source"] = "EXPLICIT SOURCE TABLE(S): " + ", ".join(tables)
    elif fields.get("reporting_source"):
        details["reporting_source"] = "EXPLICIT SOURCE: " + fields["reporting_source"]

    return details


def _ai_engine_enabled() -> bool:
    return os.environ.get("LEAP_ENABLE_AI", "0") in {"1", "true", "True"} and bool(
        os.environ.get("OPENAI_API_KEY")
    )


def _is_explicit(value: str) -> bool:
    text = (value or "").strip()
    upper = text.upper()
    return bool(text) and not any(
        marker in upper
        for marker in (
            "UNDETERMINED",
            "LINEAGE UNDETERMINED",
            "NOT DECLARED",
            "NO EXPLICIT",
            "OWNER CONFIRMATION",
        )
    )


def _optional_ai_details(
    kpi_name: str, code_context: str, deterministic: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass
        from openai import OpenAI
    except Exception:
        return deterministic

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return deterministic

    locked = {
        key: value
        for key, value in deterministic.items()
        if key in {"input_measure", "unit_of_measure", "reporting_source"}
        and _is_explicit(str(value))
    }
    prompt = f"""
You are the optional LEAP AI detail engine. Produce concise JSON for a KPI dossier.

Critical rules:
- Do not invent source systems, industries, tables, SCADA/DCS tags, ERP systems, CRM systems, or operational environments.
- If a field cannot be supported by the code or comments, keep the deterministic owner-confirmation wording. Do not use raw "UNDETERMINED" labels.
- Never override locked explicit source facts.
- Any business interpretation that is inferred from a name rather than directly stated must start with "AI DRAFT:".
- Return only JSON with these keys: {", ".join(DETAIL_KEYS)}.

KPI name:
{kpi_name}

Deterministic baseline:
{json.dumps(deterministic, ensure_ascii=False)}

Locked explicit source facts:
{json.dumps(locked, ensure_ascii=False)}

Source context:
```text
{code_context[:6000]}
```
"""
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("LEAP_AI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            timeout=20,
        )
        content = response.choices[0].message.content
        parsed = json.loads(content or "{}")
        if not isinstance(parsed, dict):
            return deterministic
    except Exception:
        return deterministic

    merged = dict(deterministic)
    for key in DETAIL_KEYS:
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    for key, value in locked.items():
        merged[key] = value
    if not _is_explicit(str(deterministic.get("reporting_source", ""))):
        proposed_source = str(merged.get("reporting_source", ""))
        if not (
            proposed_source.startswith("EXPLICIT SOURCE")
            or proposed_source == LINEAGE_UNDETERMINED
        ):
            merged["reporting_source"] = LINEAGE_UNDETERMINED
    merged["comments"] = (
        (merged.get("comments") or "").rstrip()
        + " Optional AI enrichment was enabled; AI DRAFT fields require owner validation."
    ).strip()
    return merged


def generate_kpi_details(kpi_name: str, code_context: str) -> Dict[str, Any]:
    """Return deterministic details, with optional opt-in AI draft enrichment."""
    deterministic = _deterministic_kpi_details(kpi_name, code_context)
    if not _ai_engine_enabled():
        return deterministic
    return _optional_ai_details(kpi_name, code_context, deterministic)
