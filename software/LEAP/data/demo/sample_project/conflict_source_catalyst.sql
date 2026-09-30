-- KPI: Catalyst Replacement Frequency
-- Formula: Catalyst Frequency = Total Replacements / Operating Months
-- Description: Average rate at which catalysts are replaced across all reactor units.
-- Objective: Optimize catalyst lifecycle management and reduce unplanned shutdowns.
-- Input: Count of catalyst replacement events, months of reactor operation
-- Unit: replacements/month
-- Reporting Source: SAP PM (Plant Maintenance) — PM order type ZM01
-- Used In: Maintenance Performance Dashboard, Reliability Review

-- Source system conflict: Business comment declares source system is SAP PM.
-- However this file loads data from a manual CSV export (flat-file staging area),
-- indicating the certified source does not match the declared system of record.

-- csv_stage is a flat-file import area populated by manual export — NOT SAP PM live data
SELECT
    r.unit_code,
    COUNT(r.replacement_id) AS total_replacements,
    DATEDIFF(MONTH, MIN(r.event_date), MAX(r.event_date)) + 1 AS operating_months,
    COUNT(r.replacement_id) * 1.0
        / NULLIF(DATEDIFF(MONTH, MIN(r.event_date), MAX(r.event_date)) + 1, 0)
        AS catalyst_replacement_frequency
FROM csv_stage.catalyst_replacement_log r
GROUP BY r.unit_code
ORDER BY catalyst_replacement_frequency DESC;
