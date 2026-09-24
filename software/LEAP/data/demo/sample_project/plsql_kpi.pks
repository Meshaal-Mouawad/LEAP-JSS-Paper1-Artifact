-- KPI: Yield Percentage (%)
-- Formula: \mathrm{Yield\,\%} = \frac{\mathrm{Desired\,Product}}{\mathrm{Total\,Input}} \times 100

CREATE OR REPLACE PACKAGE kpi_pkg AS
  FUNCTION yield_pct(desired_product NUMBER, total_input NUMBER) RETURN NUMBER;
END kpi_pkg;
/
CREATE OR REPLACE PACKAGE BODY kpi_pkg AS
  FUNCTION yield_pct(desired_product NUMBER, total_input NUMBER) RETURN NUMBER IS
  BEGIN
    IF total_input = 0 THEN RETURN 0; END IF;
    RETURN (desired_product / total_input) * 100;
  END;
END kpi_pkg;
/
