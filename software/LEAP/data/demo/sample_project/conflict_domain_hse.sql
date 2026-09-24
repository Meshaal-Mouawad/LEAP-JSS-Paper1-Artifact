-- KPI: HSE Safety Incident Rate
-- Formula: Safety Incident Rate = (Total Incidents / Total Hours Worked) * 200000
-- Description: OSHA-standard recordable incident rate for HSE performance tracking.
-- Objective: Monitor workforce safety performance and compliance with HSE regulations.
-- Input: Total recordable incidents, total hours worked
-- Unit: incidents per 200,000 hours
-- Reporting Source: SAP PM Safety Module, HSE incident register
-- Used In: HSE Executive Dashboard, Safety Compliance Board

-- Domain conflict: KPI intent is HSE / safety but this file is in a finance reporting path
-- and uses financial table joins suggesting Finance domain ownership conflict.

SELECT
    t.fiscal_period,
    t.cost_center,
    SUM(f.total_incidents) AS incidents_count,
    SUM(f.hours_worked) AS hours_worked,
    (SUM(f.total_incidents) * 200000.0 / NULLIF(SUM(f.hours_worked), 0)) AS hse_safety_incident_rate
FROM finance.cost_reporting_fact f
JOIN finance.time_dim t ON f.period_id = t.period_id
WHERE t.fiscal_year = YEAR(GETDATE())
GROUP BY t.fiscal_period, t.cost_center
ORDER BY t.fiscal_period;
