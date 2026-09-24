-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: A / NULLIF(B, 0)

-- KPI: Nullif Denominator Formula
-- Formula: A / NULLIF(B, 0)
-- Business Objective: Track safe ratio calculation.
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT (A / NULLIF(B, 0)) AS safe_ratio FROM metrics;
