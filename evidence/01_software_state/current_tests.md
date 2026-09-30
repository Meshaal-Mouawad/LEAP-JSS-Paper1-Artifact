# LEAP Current Software Test Evidence

**Evidence Class:** A - CURRENT SOFTWARE STATE  
**Original Inventory Date:** 2026-07-14
**Latest Reconciliation:** 2026-07-24

## Current Verification Override

The detailed 57-case inventory below is the July 14 baseline and is retained for
traceability. It is no longer the latest whole-suite count.

Latest preserved evidence:

- QA-001 full live product suite: 117 passed.
- RR-009 focused Phase 5 suite: 35 passed.
- RR-009 governed rewrite capability matrix: 38/38 passed.
- QA-001 Phase 3 governance/compliance selection: 8 passed.
- QA-001 simulation and Zero-Code selection: 14 passed.
- QA-001 generation regression: passed.
- QA-001 human visual condition: satisfied on 2026-07-24.

See `SOFTWARE_STATE_UPDATE_2026-07-24.md`, RR-009, and QA-001. The counts above
come from preserved records and must not be added together as if they were
disjoint test cases.

## Historical July 14 Test Summary

- **Total Test Files:** 2
- **Total Test Functions / Scenarios:** 57
- **Passed:** 57
- **Failed:** 0
- **Pass Rate:** 100%

## Test Suite 1: Flask Application Tests (test_app.py)

### Test Coverage
- **File:** `test_app.py`
- **Test Count:** 19
- **Framework:** pytest
- **Execution Time:** 0.08s
- **Status:** ALL PASSED

### Test Functions

#### 1. test_control_plane_routes_are_available
- **Behavior Tested:** Flask route availability
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** N/A
- **Expected Result:** HTTP 200 on `/`, `/status`, `/api/stats`
- **Actual Result:** HTTP 200 returned
- **JSS Claim Supported:** System availability

#### 2. test_workspace_stats_payload_shape
- **Behavior Tested:** API payload structure
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** N/A
- **Expected Result:** Valid JSON with total_kpis, validated_kpis, review_items, avg_confidence, workspace_state
- **Actual Result:** Valid JSON structure returned
- **JSS Claim Supported:** API reliability

#### 3. test_committed_bluebook_pages_are_served
- **Behavior Tested:** HTML page serving
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** N/A
- **Expected Result:** HTTP 200 on Bluebook pages
- **Actual Result:** HTTP 200 returned
- **JSS Claim Supported:** Documentation generation

#### 4. test_bluebook_static_assets_are_served
- **Behavior Tested:** Static asset serving
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** N/A
- **Expected Result:** HTTP 200 on CSS/SVG assets
- **Actual Result:** HTTP 200 returned
- **JSS Claim Supported:** Asset delivery

#### 5. test_enterprise_workspace_assets_are_present
- **Behavior Tested:** Build artifact verification
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** N/A
- **Expected Result:** Required files exist in docs/_build
- **Actual Result:** All files exist
- **JSS Claim Supported:** Build integrity

#### 6. test_compliance_alarms_pdpl_pii (positive case)
- **Behavior Tested:** KSA-PDPL-REG-01 PII detection
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Positive: PII without masking
- **Expected Result:** Alarm triggered
- **Actual Result:** Alarm triggered
- **JSS Claim Supported:** Compliance detection

#### 7. test_compliance_alarms_pdpl_pii (clean control)
- **Behavior Tested:** KSA-PDPL-REG-01 clean control
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Clean: PII with masking
- **Expected Result:** No alarm
- **Actual Result:** No alarm
- **JSS Claim Supported:** PDPL clean-control behavior

#### 8. test_compliance_alarms_nca_sec (positive case)
- **Behavior Tested:** KSA-NCA-ECC-SEC-04 security detection
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Positive: os.system/eval
- **Expected Result:** Alarm triggered
- **Actual Result:** Alarm triggered
- **JSS Claim Supported:** Security detection

#### 9. test_compliance_alarms_nca_sec (clean control)
- **Behavior Tested:** KSA-NCA-ECC-SEC-04 clean control
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Clean: safe code
- **Expected Result:** No alarm
- **Actual Result:** No alarm
- **JSS Claim Supported:** NCA security clean-control behavior

#### 10. test_compliance_alarms_nca_aud (positive case)
- **Behavior Tested:** KSA-NCA-ECC-AUD-02 audit gap detection
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Positive: update without audit
- **Expected Result:** Alarm triggered
- **Actual Result:** Alarm triggered
- **JSS Claim Supported:** Audit detection

#### 11. test_compliance_alarms_nca_aud (clean control)
- **Behavior Tested:** KSA-NCA-ECC-AUD-02 clean control
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Clean: update with audit
- **Expected Result:** No alarm
- **Actual Result:** No alarm
- **JSS Claim Supported:** NCA audit clean-control behavior

#### 12. test_compliance_alarms_gdpr_proc (positive case)
- **Behavior Tested:** GDPR-DATA-PROC-01 data transfer detection
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Positive: cross_border without consent
- **Expected Result:** Alarm triggered
- **Actual Result:** Alarm triggered
- **JSS Claim Supported:** Regulatory detection

#### 13. test_compliance_alarms_gdpr_proc (clean control)
- **Behavior Tested:** GDPR-DATA-PROC-01 clean control
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Clean: transfer with agreement
- **Expected Result:** No alarm
- **Actual Result:** No alarm
- **JSS Claim Supported:** GDPR clean-control behavior

#### 14. test_compliance_alarms_soc2_lineage (positive case)
- **Behavior Tested:** SOC2-LINEAGE-AUD-01 signature detection
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Positive: lineage without signature
- **Expected Result:** Alarm triggered
- **Actual Result:** Alarm triggered
- **JSS Claim Supported:** Audit detection

#### 15. test_compliance_alarms_soc2_lineage (clean control)
- **Behavior Tested:** SOC2-LINEAGE-AUD-01 clean control
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Clean: lineage with signature
- **Expected Result:** No alarm
- **Actual Result:** No alarm
- **JSS Claim Supported:** SOC 2 clean-control behavior

#### 16. test_review_queue_signal_separation (clean KPI)
- **Behavior Tested:** Clean KPI no conflicts
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** Clean KPI with formula
- **Expected Result:** No conflicts/notes/alarms
- **Actual Result:** No conflicts/notes/alarms
- **JSS Claim Supported:** Signal separation

#### 17. test_review_queue_signal_separation (missing formula)
- **Behavior Tested:** Missing formula medium note
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** KPI without formula comment
- **Expected Result:** Medium audit note
- **Actual Result:** Medium audit note
- **JSS Claim Supported:** Signal separation

#### 18. test_review_queue_signal_separation (TODO/FIXME)
- **Behavior Tested:** TODO/FIXME technical note
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** KPI with TODO comment
- **Expected Result:** Medium audit note
- **Actual Result:** Medium audit note
- **JSS Claim Supported:** Signal separation

#### 19. test_review_queue_signal_separation (governance conflict)
- **Behavior Tested:** Governance conflict high severity
- **Deterministic or Agent Path:** Deterministic
- **Current Status:** PASSED
- **Fixture Used:** HSE KPI with finance tables
- **Expected Result:** High conflict
- **Actual Result:** High conflict
- **JSS Claim Supported:** Signal separation

## Test Suite 2: Scenario Fixture Tests (phase3/test_scenario_fixtures.py)

### Test Coverage
- **File:** `phase3/test_scenario_fixtures.py`
- **Test Count:** 38 scenario fixtures
- **Framework:** pytest (standalone execution)
- **Execution Time:** ~2s
- **Status:** ALL PASSED

### Scenario Fixtures

#### Clean Controls (Validated)
1. **01_clean_python_kpi.py** - Clean Python KPI → Validated
2. **02_clean_sql_kpi.sql** - Clean SQL KPI → Validated
3. **03_clean_abap_kpi.abap** - Clean ABAP KPI → Validated
4. **12_suspicious_fallback.py** - Suspicious fallback handling → Validated
5. **18_pdpl_clean_control.py** - KSA-PDPL-REG-01 clean control → Validated
6. **19_nca_restricted_clean_control.py** - KSA-NCA-ECC-SEC-04 clean control → Validated
7. **20_audit_clean_control.py** - KSA-NCA-ECC-AUD-02 clean control → Validated
8. **21_gdpr_clean_control.py** - GDPR-DATA-PROC-01 clean control → Validated
9. **22_soc2_clean_control.py** - SOC2-LINEAGE-AUD-01 clean control → Validated
10. **28_validated_clean.sql** - Validated clean SQL → Validated
11. **29_simple_ratio.sql** - Simple ratio formula → Validated
12. **30_percentage_ratio.sql** - Percentage ratio formula → Validated
13. **31_multiplication_formula.sql** - Multiplication formula → Validated
14. **32_subtraction_formula.sql** - Subtraction formula → Validated
15. **33_nullif_denominator.sql** - NULLIF denominator → Validated
16. **34_case_sum_count.sql** - CASE with SUM/COUNT → Validated
17. **35_explicit_latex.py** - Explicit LaTeX formula → Validated
18. **36_formula_with_underscores.sql** - Formula with underscores → Validated
19. **37_formula_with_units.sql** - Formula with units → Validated
20. **38_greek_symbols.py** - Greek symbols in formula → Validated

#### Governance Conflicts (Needs Review)
21. **04_wrong_operator.sql** - Wrong operator detection → Needs Review
22. **05_wrong_numerator.sql** - Wrong numerator detection → Needs Review
23. **06_wrong_denominator.sql** - Wrong denominator detection → Needs Review

#### Evidence Completeness (Needs Review)
24. **07_missing_formula_comment.sql** - Missing formula detection → Needs Review
25. **08_missing_implementation.py** - Missing implementation detection → Needs Review
26. **27_owner_confirmation_required.py** - Owner confirmation → Needs Review

#### Technical Review (Needs Review)
27. **09_todo_kpi.py** - TODO detection → Needs Review
28. **10_fixme_kpi.py** - FIXME detection → Needs Review
29. **11_bug_kpi.py** - BUG detection → Needs Review

#### Compliance Alarms (Needs Review)
30. **13_pdpl_pii_violation.py** - KSA-PDPL-REG-01 detection → Needs Review
31. **14_nca_restricted_exec.py** - KSA-NCA-ECC-SEC-04 detection → Needs Review
32. **15_nca_audit_gap.py** - KSA-NCA-ECC-AUD-02 detection → Needs Review
33. **16_gdpr_data_export_violation.py** - GDPR-DATA-PROC-01 detection → Needs Review
34. **17_soc2_unsigned_lineage.py** - SOC2-LINEAGE-AUD-01 detection → Needs Review

#### Signal Composition (Needs Review)
35. **23_formula_conflict_and_todo.sql** - Combined signals → Needs Review
36. **24_compliance_and_formula_conflict.sql** - Combined signals → Needs Review
37. **25_compliance_alarm_only.py** - Compliance only → Needs Review
38. **26_technical_review_only.py** - Technical review only → Needs Review

## Test Coverage Analysis

### Deterministic Engine Coverage
- **Source Discovery:** Covered via scenario fixtures
- **Language Routing:** Covered via multi-language fixtures
- **Formula Extraction:** Covered via formula rendering tests
- **Governance Validation:** Covered via conflict detection tests
- **Compliance Alarms:** Covered via 5 framework tests
- **Review Queue:** Covered via signal separation tests

### Optional Agent Coverage
- **AI Enrichment:** Limited coverage (requires API key)
- **Draft Validation:** Not explicitly tested

### Missing Test Coverage
- Performance benchmarks
- Scalability tests
- Ablation studies (tag-only vs inference-only vs hybrid)
- Gold-standard validation
- End-to-end Bluebook generation verification
- Source link resolution validation

## Conclusion

The archived inventory provides **broad deterministic behavior coverage** with 57 passing cases covering:
- Flask application routes and API
- Static asset serving
- Build integrity
- Five tested rule scenarios across four named families (KSA-PDPL, KSA-NCA-ECC, GDPR, and SOC 2)
- Governance conflict detection
- Review queue signal separation
- Multi-language support (Python, SQL, ABAP)
- Formula rendering and normalization

**Test Reliability:** 100% pass rate across both test suites  
**Execution Speed:** Fast (0.08s for Flask tests, ~2s for scenario fixtures)  
**Maintenance:** Good - fixtures are self-documenting with expected results

## JSS Frozen-Snapshot Extension (QA-003, 2026-09-20)

The frozen JSS snapshot adds four focused deterministic regression tests:

- two MATE source-to-rendering tests;
- one ISO-22400-RE-1 yield rule test with positive and clean controls;
- one ISO-22400-UE-2 asset-utilization rule test with positive and clean controls.

The resulting frozen-snapshot run passed 19 pytest checks, all 38 controlled scenarios, sample generation, validation of 32 generated pages with zero errors and warnings, and six local route checks. These results establish bounded implementation behavior, not formula accuracy, extraction precision/recall, certification, or exhaustive ISO 22400 coverage.
