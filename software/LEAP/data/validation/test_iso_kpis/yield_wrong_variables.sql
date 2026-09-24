-- KPI: Yield Rate (Wrong Variables)
SELECT 
    (scrap_mass / raw_input_mass) * 100 AS yield_rate
FROM production_data;