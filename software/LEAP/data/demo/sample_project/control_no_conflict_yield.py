# KPI: Ethylene Production Yield
# Formula: Ethylene Yield % = (Ethylene Produced (tons) / Feedstock Input (tons)) * 100
# Description: Percentage of feedstock mass successfully converted to ethylene product.
# Objective: Maximize conversion efficiency in the steam cracking unit within safe operating limits.
# Input: Ethylene produced (tons), Feedstock input (tons)
# Unit: %
# Reporting Source: DCS Historian (OSIsoft PI) and shift production logs
# Used In: Operations Performance Dashboard, Cracker Unit KPI Review
# Accountable Owner: Operations Data Owner

# Control: no conflict. Business formula and implementation agree.
# Business comment declares percentage formula (numerator / denominator * 100).
# Code below implements exactly that logic.

def calculate_ethylene_yield_pct(ethylene_produced_tons: float, feedstock_input_tons: float) -> float:
    """Calculates ethylene production yield as a percentage of feedstock input."""
    if feedstock_input_tons <= 0:
        return 0.0
    return (ethylene_produced_tons / feedstock_input_tons) * 100.0
