* KPI: Permit To Work Closure Compliance
* Business Definition: Measures percentage of PTW records closed within required safety window.
* Formula: Closed_On_Time_PTW / Total_PTW * 100
* Accountable Owner: HSE Data Owner
* Source System: SAP EHS
* Direction: Higher is better

DATA compliance TYPE p DECIMALS 2.
SELECT COUNT(*) FROM zfin_ptw_stage INTO @DATA(total_ptw).
SELECT COUNT(*) FROM zfin_ptw_stage WHERE closed_on_time = 'X' INTO @DATA(closed_on_time).
compliance = closed_on_time / total_ptw * 100.
