-- KPI: Rolling 30 Day On-Spec Rate
-- Business Definition: Percent of batches on-spec over the last rolling 30 days.
-- Formula: OnSpec_Batches_Last_30_Days / Total_Batches_Last_30_Days * 100
-- Accountable Owner: Quality Data Owner
-- Source System: LIMS
-- Direction: Higher is better

SELECT
    SUM(CASE WHEN batch_status = 'ON_SPEC' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS rolling_30_day_onspec_rate
FROM lims.batch_quality
WHERE batch_date >= CURRENT_DATE - INTERVAL '90 day';
