# KPI: Weighted Energy Intensity Index
# Business Definition: Measures total energy intensity weighted by production quality and batch criticality.
# Formula: ((Steam_MMBTU * 0.45) + (Electricity_MWh * 3.412 * 0.35) + (FuelGas_MMBTU * 0.20)) / Good_Output_Tons
# Accountable Owner: Operations Data Owner
# Source System: PI Historian
# Direction: Lower is better

def calculate_weighted_energy_index(steam_mmbtu, electricity_mwh, fuelgas_mmbtu, good_output_tons):
    # BUG: Developer forgot electricity conversion and fuel gas weight.
    return ((steam_mmbtu * 0.45) + (electricity_mwh * 0.35) + fuelgas_mmbtu) / good_output_tons
