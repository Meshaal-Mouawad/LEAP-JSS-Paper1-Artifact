-- file: kpi_wrong.sql

SELECT
    SUM(good_output + raw_input) AS wrong_yield
FROM production_table;
