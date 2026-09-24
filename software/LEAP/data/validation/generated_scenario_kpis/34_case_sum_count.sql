-- Expected LEAP Result:
-- - Governance Status: Validated
-- - Review Queue: No
-- - Expected Signal(s): None
-- - Expected Compliance Rule(s): None
-- - Expected Formula Behavior: SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END) / COUNT(score)

-- KPI: NPS Pattern Formula
-- Formula: SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END) / COUNT(score)
-- Business Objective: Track promoter score calculation.
-- Owner: Customer Experience Data Owner
-- Source System: SAP PM

SELECT (SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END) / COUNT(score)) AS nps_metric FROM feedback_table;
