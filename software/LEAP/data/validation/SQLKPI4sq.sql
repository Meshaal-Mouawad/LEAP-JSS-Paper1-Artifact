-- file: kpi_output.sql

SELECT
    SUM(good_output) / SUM(raw_input) * 100 AS yield_percentage
FROM production_table;
``