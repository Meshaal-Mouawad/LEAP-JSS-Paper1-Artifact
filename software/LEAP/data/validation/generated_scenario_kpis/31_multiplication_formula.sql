-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: A * B * C

-- KPI: Multiplication Formula
-- Formula: A * B * C
-- Business Objective: Track multiplication calculation.
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT (A * B * C) AS multiplication FROM metrics;
