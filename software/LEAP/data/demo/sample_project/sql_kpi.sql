-- KPI: On-Spec Rate (%)
-- Formula: \mathrm{On\text{-}Spec\,\%} = \frac{\mathrm{On\text{-}Spec\,Batches}}{\mathrm{Total\,Batches}} \times 100
CREATE VIEW kpi_on_spec_rate AS
SELECT
    CAST(100.0 * on_spec_batches / NULLIF(total_batches, 0) AS FLOAT) AS on_spec_percentage
FROM batch_quality_summary;
