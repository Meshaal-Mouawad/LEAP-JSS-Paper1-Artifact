# LEAP Governance Conflict System — Test Fixture Diagnosis

**Date:** 2026-07-06
**Branch:** ui-freeze-v1
**Scope:** 7 synthetic KPI fixtures created in `sample_project/`, generation run, pytest executed.

---

## 1. Fixtures Created

| File | Scenario | Expected Conflict |
|---|---|---|
| `conflict_formula_margin.py` | Business: (Revenue-Cost)/Revenue×100, Code: Revenue/Cost×100 | Formula operator conflict |
| `conflict_domain_hse.sql` | HSE safety KPI routed through Finance tables | Domain ownership conflict |
| `conflict_owner_hse.abap` | Comment declares HSE Data Owner; governance rules may infer Finance | Owner accountability conflict |
| `conflict_source_catalyst.sql` | Comment says SAP PM; code reads `csv_stage.*` (manual CSV) | Source lineage conflict |
| `conflict_threshold_vibration.py` | Higher value = degradation (bad), code labels high as GOOD_PERFORMANCE | Threshold interpretation conflict |
| `conflict_validation_compliance.sql` | No Formula: comment present, status shown as Validated | Validation status conflict |
| `control_no_conflict_yield.py` | Business formula and code implementation fully agree | No conflict (control) |

---

## 2. Generation Results

All 7 fixture KPIs were detected. 19 total KPIs generated. pytest: 5/5 passed.

| Fixture KPI Name | Detected | Confidence |
|---|---|---|
| Gross Margin Percentage | YES | 95% |
| HSE Safety Incident Rate | YES | 95% |
| Flare Emission Recovery Rate | YES | 95% |
| Catalyst Replacement Frequency | YES | 95% |
| Compressor Vibration Index | YES | 95% |
| Procurement Contract Compliance Rate | YES | 95% |
| Ethylene Production Yield | YES | 95% |

---

## 3. Governance Alarms Observed

### 3.1 governance_patch.evaluate_logic — High-Severity Path
Result: 0 High-severity conflicts triggered.

Root cause: evaluate_logic reads details.get("business_formula", "").
Details dict from _deterministic_kpi_details stores formula under "formula_description" not "business_formula".
Key mismatch means evaluate_logic always reads empty string → conflicts = [].

### 3.2 formula_mismatch Flag
Result: False for all KPIs, including the formula conflict fixture.

Root cause for Gross Margin: main.py source_ops extraction includes comment lines containing
the word "formula". The "# Formula: (Revenue - Cost) / Revenue * 100" line itself contains "-",
so source_ops_normalized includes "-". This matches description_ops — mismatch test returns False.
The formula declaration comment self-injects the missing operator into evidence.

### 3.3 .gov-conflict-subpanel HTML Card
Result: Not rendered. kpi.governance.conflicts is always [] → both template guards false.

### 3.4 Governance Status Badge
Result: All 7 KPIs show "Validated". No conflicts detected → status = Validated.

---

## 4. Per-Scenario Results

### Scenario 1 — Formula Conflict (Gross Margin Percentage)
TRIGGERED: NO — no conflict card, Validated status
WHY MISSED: # Formula: comment line pollutes source_ops_normalized. Declared formula operators
contaminate evidence set. Mismatch test cannot separate comment operators from code operators.
RACI: Enterprise Data Owner (default — "margin/gross" not in any rule)

### Scenario 2 — Domain Conflict (HSE Safety via Finance tables)
TRIGGERED: NO — no conflict card
WHY MISSED: No source-table domain inference exists. Name rule correctly assigns HSE Data Owner
from "hse"/"safety" keywords. Finance table name (finance.cost_reporting_fact) is not checked.
NOTE: RACI was correct here — conflict exists only at schema level (not implemented).

### Scenario 3 — Owner Conflict (Flare Emission Recovery Rate)
TRIGGERED: NO — RACI correctly shows HSE Data Owner
WHY MISSED: _explicit_comment_fields() does not parse "Accountable Owner:" key.
No comment-vs-rule owner comparison mechanism exists.

### Scenario 4 — Source System Conflict (Catalyst vs SAP PM)
TRIGGERED: NO — no conflict card
WHY MISSED: Source system conflict detection is not implemented. "Reporting Source:" is
displayed as plain text only. No comparison with actual table/schema references in SQL.
RACI: Enterprise Data Owner (default — "catalyst/replacement" not in any rule)

### Scenario 5 — Threshold Conflict (Compressor Vibration Index)
TRIGGERED: NO — no conflict card
WHY MISSED: Threshold direction analysis is not implemented. The "# BUG:" annotation check
in governance_patch.py line 35 searches for " BUG " with spaces on both sides; "# BUG:"
has colon, not trailing space — regex fails to match.
RACI: Maintenance Data Owner (correctly inferred from "compressor" name rule)

### Scenario 6 — Validation Conflict (Procurement Contract Compliance)
TRIGGERED: NO — shown as Validated, no conflict
WHY MISSED: Without "# Formula:" comment, _looks_like_formula() returns False → formula_mismatch
never evaluated. Validated status is awarded if governance_accountable is non-empty.
Formula presence is never required for Validated status.

### Scenario 7 — Control (Ethylene Production Yield)
TRIGGERED: NO conflict card — CORRECT (expected behavior)
RACI: Operations Data Owner (path rule: "ethylene") — CORRECT
Status: Validated — CORRECT

---

## 5. System Architecture Gap Summary

| Conflict Type | Mechanism | Fires | Root Cause |
|---|---|---|---|
| Formula operator mismatch | formula_mismatch in main.py | NO | Comment lines with "formula" keyword pollute source_ops |
| governance_patch High conflict | evaluate_logic() | NO | Key mismatch: reads "business_formula", dict has "formula_description" |
| ISO template conflict | iso_framework.json | NO | Only 4 templates; none cover margin/incident/vibration/compliance |
| Source system vs actual | NOT IMPLEMENTED | — | No schema-domain comparison |
| Owner comment vs RACI rule | NOT IMPLEMENTED | — | _explicit_comment_fields skips "Accountable Owner:" |
| Threshold direction inversion | NOT IMPLEMENTED | — | No semantic label analysis |
| Validation without formula | NOT IMPLEMENTED | — | Validated status only checks accountable is non-empty |
| BUG/TODO annotation scan | governance_patch.py L35 | NO | Regex " BUG " needs spaces; "# BUG:" has colon instead |

---

## 6. What Did Render (All KPIs)

YES: Formal formula block (LaTeX via math-equation div, rendered from # Formula: comment)
YES: RACI assignment (HSE, Maintenance, Operations owners correctly inferred)
YES: Governance status badge (all Validated — mechanically correct given no conflicts)
YES: Discovery report and RACI directory updated with 19 KPIs
NO:  .gov-conflict-subpanel — never rendered
NO:  #governance-review-note — static HTML block suppressed for all KPIs

---

## 7. Pytest Results

5 passed in 0.06s. No regressions.

---

## 8. Fixtures Are Safe to Remove

The 7 test fixture files live only in sample_project/. No CSS, templates, or existing pages were touched.
