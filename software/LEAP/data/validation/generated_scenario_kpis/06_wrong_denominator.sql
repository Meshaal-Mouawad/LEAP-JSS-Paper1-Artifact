-- Expected LEAP Result:
-- - Governance Status: Needs Review
-- - Review Queue: Yes
-- - Expected Signal(s): asset utilization variable conflict
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: Expected planned_operation_time as denominator

-- KPI: Asset Utilization
-- Formula: actual_run_time / planned_operation_time
-- Business Objective: Measure machinery utilization.
-- Owner: Maintenance Data Owner
-- Source System: SAP PM

SELECT (actual_run_time / total_run_time) AS asset_utilization FROM asset_table;
