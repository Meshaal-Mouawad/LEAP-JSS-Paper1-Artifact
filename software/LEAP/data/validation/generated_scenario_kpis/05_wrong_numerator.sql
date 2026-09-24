-- Expected LEAP Result:
-- - Governance Status: Needs Review
-- - Review Queue: Yes
-- - Expected Signal(s): variable conflict
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: Expected good_output_mass as numerator

-- KPI: Yield Rate
-- Formula: good_output_mass / raw_input_mass
-- Business Objective: Track yield rate of production line.
-- Owner: Operations Data Owner
-- Source System: SAP PP

SELECT (scrap_mass / raw_input_mass) AS yield_efficiency FROM yield_table;
