# Expected LEAP Result:
# - Governance Status: Validated
# - Review Queue: No
# - Expected Signal(s): None
# - Expected Compliance Rule(s): None
# - Expected Formula Behavior: A / B

# KPI: Clean Python KPI
# Formula: A / B
# Business Objective: Track percentage of prime quality product.
# Owner: Enterprise Data Owner
# Source System: LIMS

def calc(A, B):
    if B is None or B == 0:
        return 999.9  # Suspicious fallback but no rule violation
    return A / B
