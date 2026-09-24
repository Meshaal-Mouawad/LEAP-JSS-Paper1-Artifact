-- KPI: Emergency Shutdown Demand Rate
-- Business Definition: Counts ESD demands per operating month.
-- Formula: ESD_Demands / Operating_Months
-- Accountable Owner: HSE Data Owner
-- Source System: Safety Instrumented System
-- Direction: Higher is worse

SELECT
    CASE
        WHEN esd_demands / NULLIF(operating_months, 0) > 0.05 THEN 'GOOD_PERFORMANCE'
        ELSE 'NEEDS_ATTENTION'
    END AS esd_status,
    esd_demands / NULLIF(operating_months, 0) AS emergency_shutdown_demand_rate
FROM finance.monthly_operating_summary;
