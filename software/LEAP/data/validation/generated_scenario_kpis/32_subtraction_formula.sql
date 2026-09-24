-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: outlet - inlet

-- KPI: Subtraction Formula
-- Formula: outlet - inlet
-- Business Objective: Track delta calculation.
-- Owner: Enterprise Data Owner
-- Source System: SAP PM

SELECT (outlet - inlet) AS delta FROM sensor_logs;
