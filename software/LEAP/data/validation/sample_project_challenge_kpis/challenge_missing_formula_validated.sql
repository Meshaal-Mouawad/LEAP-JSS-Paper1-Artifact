-- KPI: Critical Spare Readiness
-- Business Definition: Percentage of critical spare parts available at or above minimum stock level.
-- Accountable Owner: Maintenance Data Owner
-- Source System: SAP MM
-- Governance Status: Validated
-- Direction: Higher is better

SELECT
    SUM(CASE WHEN on_hand_qty >= min_stock_qty THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS critical_spare_readiness
FROM sap_mm.critical_spares;
