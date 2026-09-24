-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: SELECT actual_output / target_output

-- KPI: Validated Clean
-- Formula: actual_output / target_output
-- Business Objective: Track operations KPI
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT (actual_output / target_output) AS target_achievement FROM production_logs;
