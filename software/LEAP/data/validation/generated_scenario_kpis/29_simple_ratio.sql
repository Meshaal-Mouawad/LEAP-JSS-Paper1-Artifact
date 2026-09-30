-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: A / B

-- KPI: Simple Ratio
-- Formula: A / B
-- Business Objective: Track simple ratio.
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT (A / B) AS ratio FROM metrics;
