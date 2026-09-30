# Expected LEAP Result:
# - Governance Status: Validated
# - Review Queue: No
# - Expected Signal(s): None
# - Expected Compliance Rule(s): None
# - Expected Formula Behavior: outlet_temp - inlet_temp

# KPI: Units Formula
# Formula: outlet_temp - inlet_temp
# Business Objective: Track temperature delta.
# Owner: Enterprise Data Owner
# Source System: SAP PM
# Unit: °C

def calc(outlet_temp, inlet_temp):
    return outlet_temp - inlet_temp
