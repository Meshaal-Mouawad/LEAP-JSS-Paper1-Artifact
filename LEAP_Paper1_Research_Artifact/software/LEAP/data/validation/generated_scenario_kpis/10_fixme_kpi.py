# Expected LEAP Result:
# - Governance Status: Needs Review
# - Review Queue: Yes
# - Expected Signal(s): Found potential development issues (BUG/TODO/FIXME)
# - Expected Compliance Rule(s): None
# - Expected Formula Behavior: A / B

# KPI: Clean Python KPI
# Formula: A / B
# Business Objective: Track percentage of prime quality product.
# Owner: Enterprise Data Owner
# Source System: LIMS

# FIXME: Resolve divide by zero error for negative inputs
def calc(A, B):
    return A / B
