-- Expected LEAP Result:
-- - Governance Status: Needs Review
-- - Review Queue: Yes
-- - Expected Signal(s): operator conflict
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: Expected division but found addition

-- KPI: Yield Rate
-- Formula: good_output_mass / raw_input_mass
-- Business Objective: Track yield rate of production line.
-- Owner: Operations Data Owner
-- Source System: SAP PP

SELECT (good_output_mass + raw_input_mass) AS yield_efficiency FROM yield_table;
