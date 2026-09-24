-- Expected LEAP Result:
-- - Governance Status: Needs Review
-- - Review Queue: Yes
-- - Expected Signal(s): Evidence incomplete: business formula comment not declared.
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: Inferred SELECT A / B

-- KPI: Asset Utilization
-- Business Objective: Measure machinery utilization.
-- Owner: Maintenance Data Owner
-- Source System: SAP PM

SELECT (actual_run_time / planned_operation_time) AS asset_utilization FROM asset_table;
