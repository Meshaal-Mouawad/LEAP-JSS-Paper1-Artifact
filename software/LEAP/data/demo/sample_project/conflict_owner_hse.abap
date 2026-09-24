* KPI: Flare Emission Recovery Rate
* Formula: Flare Recovery % = (Gas Recovered / Total Flared) * 100
* Description: Measures the fraction of flared gas captured and returned to process.
* Objective: Reduce atmospheric flaring and improve environmental compliance under HSE mandate.
* Input: Gas recovered (m3), Total gas flared (m3)
* Unit: %
* Reporting Source: SAP PM Flare Management, DCS historian
* Accountable Owner: HSE Data Owner
* Used In: HSE Compliance Report, Environmental Dashboard

* Owner conflict: Business comment declares HSE Data Owner as accountable,
* but governance rule infers Finance Data Owner based on 'recovery' keyword
* mapping to financial domain in governance_rules.json name_rules.

DATA: lv_recovered TYPE f VALUE 320.0,
      lv_total_flared TYPE f VALUE 500.0,
      lv_recovery_pct TYPE f.

lv_recovery_pct = ( lv_recovered / lv_total_flared ) * 100.
WRITE: / 'Flare Recovery Rate (%):', lv_recovery_pct.
