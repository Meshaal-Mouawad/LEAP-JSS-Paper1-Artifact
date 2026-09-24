-- KPI: Procurement Contract Compliance Rate
-- Description: Fraction of procurement transactions executed under approved framework contracts.
-- Objective: Enforce procurement governance and maximize contract utilization.
-- Input measure: On-contract spend, total procurement spend
-- Unit: %
-- Reporting Source: SAP MM (Materials Management)
-- Used In: Procurement Governance Dashboard

-- Validation conflict: Governance status is marked Validated below but no formal
-- mathematical formula is declared anywhere in this file. The formula field is missing.
-- LEAP should flag: KPI marked Validated but formula is absent — validation conflict.

SELECT
    vendor_code,
    SUM(contract_spend) AS on_contract_spend_sar,
    SUM(total_spend) AS total_spend_sar,
    -- No explicit formula comment: formula is inferred from code only, not declared
    SUM(contract_spend) * 100.0 / NULLIF(SUM(total_spend), 0) AS procurement_contract_compliance_rate
FROM sap_mm.purchase_order_fact
WHERE fiscal_year = YEAR(GETDATE())
GROUP BY vendor_code;

-- Governance status: Validated (intentionally mismatched — no formula declared above)
