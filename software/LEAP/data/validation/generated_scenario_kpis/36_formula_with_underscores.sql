-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: total_gross_weight / net_tare_weight

-- KPI: Underscores Formula
-- Formula: total_gross_weight / net_tare_weight
-- Business Objective: Track weight ratio.
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT (total_gross_weight / net_tare_weight) AS weight_ratio FROM logistics;
