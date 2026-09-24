* Expected LEAP Result:
* - Governance Status: Validated
* - Review Queue: No
* - Expected Signal(s): None
* - Expected Compliance Rule(s): None
* - Expected Formula Behavior: actual_hours / planned_hours

* KPI: Clean ABAP KPI
* Formula: actual_hours / planned_hours
* Business Objective: Track maintenance execution schedule variance.
* Owner: Enterprise Data Owner
* Source System: SAP PM
* Unit: Ratio

METHOD calculate_variance.
  IF planned_hours > 0.
    variance = actual_hours / planned_hours.
  ELSE.
    variance = 0.
  ENDIF.
ENDMETHOD.
