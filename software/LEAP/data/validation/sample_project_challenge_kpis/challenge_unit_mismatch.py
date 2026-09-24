# KPI: CO2 Emissions Intensity
# Business Definition: Measures CO2 emissions per ton of production.
# Formula: CO2_kg / Production_Tons
# Accountable Owner: HSE Data Owner
# Source System: Environmental Data Lake
# Unit: kg CO2 / ton
# Direction: Lower is better

def calculate_co2_intensity(co2_metric_tons, production_tons):
    # Developer uses metric tons of CO2 directly instead of converting to kg.
    return co2_metric_tons / production_tons
