# Expected LEAP Result:
# - Governance Status: Validated
# - Review Queue: No
# - Expected Signal(s): None
# - Expected Compliance Rule(s): None
# - Expected Formula Behavior: onspec_rate = onspec_mass / total_mass

# KPI: Clean Python KPI
# Formula: onspec_rate = onspec_mass / total_mass
# Business Objective: Track percentage of prime quality product.
# Owner: Enterprise Data Owner
# Source System: LIMS
# Unit: %

def calculate_onspec_rate(onspec_mass, total_mass):
    if total_mass <= 0:
        return 0.0
    return (onspec_mass / total_mass) * 100.0
