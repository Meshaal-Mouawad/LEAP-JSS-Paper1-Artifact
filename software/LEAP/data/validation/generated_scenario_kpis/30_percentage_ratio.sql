-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: (A / B) * 100

-- KPI: Percentage Ratio
-- Formula: (A / B) * 100
-- Business Objective: Track percentage ratio.
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT ((A / B) * 100) AS percentage FROM metrics;
