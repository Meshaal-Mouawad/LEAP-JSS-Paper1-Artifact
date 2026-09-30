-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: SELECT good_tons / total_tons

-- KPI: Clean SQL KPI
-- Formula: good_tons / total_tons
-- Business Objective: Measure overall quality yield.
-- Owner: Enterprise Data Owner
-- Source System: MES
-- Unit: Ratio

SELECT (good_tons / total_tons) AS quality_yield FROM production_summary;
