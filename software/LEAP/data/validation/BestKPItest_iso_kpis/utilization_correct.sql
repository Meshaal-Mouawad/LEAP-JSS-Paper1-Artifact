-- KPI: Asset Utilization
SELECT
    actual_production_time / planned_operation_time AS utilization
FROM operations_data;
``