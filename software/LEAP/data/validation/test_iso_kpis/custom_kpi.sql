-- KPI: Customer Growth Rate
SELECT 
    (new_customers / total_customers) * 100 AS growth_rate
FROM crm_data;