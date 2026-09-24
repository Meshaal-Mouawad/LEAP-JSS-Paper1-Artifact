-- KPI: Yield Rate (Correct)
SELECT 
    (good_output_mass / raw_input_mass) * 100 AS yield_rate
FROM production_data;