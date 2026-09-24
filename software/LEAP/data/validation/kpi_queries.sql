-- ✅ Case A: CLEAN KPI (no mismatch)
SELECT
    SUM(good_units) * 1.0 / SUM(total_units) AS yield
FROM production_data;

-- ✅ Case B: Governance conflict only (code is fine)
SELECT
    SUM(output_units) * 1.0 / SUM(input_units) AS throughput
FROM production_data;

-- ✅ Case C: Definition mismatch
SELECT
    SUM(scrap_units) * 1.0 / SUM(total_units) AS yield_rate
FROM production_data;

-- ✅ Case D: BOTH (different logic + conflicting governance)
SELECT
    SUM(revenue) - SUM(cost) AS profit_margin
FROM finance_data;

-- ✅ Case E: Equivalent but different naming (should NOT mismatch)
SELECT
    SUM(good_units) * 1.0 / SUM(total_units) AS production_yield
FROM production_data;