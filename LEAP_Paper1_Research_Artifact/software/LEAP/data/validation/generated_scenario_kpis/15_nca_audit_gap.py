# Expected LEAP Result:
# - Governance Status: Needs Review
# - Review Queue: Yes
# - Expected Signal(s): Compliance Conflict
# - Expected Compliance Rule(s): KSA-NCA-ECC-AUD-02
# - Expected Formula Behavior: A / B

# KPI: NCA Audit Gap
# Formula: A / B
# Business Objective: Track operations KPI
# Owner: Enterprise Data Owner
# Source System: SAP PM

def modify_value(val, A, B):
    # Triggers compliance rules since we do database writes
    with open("audit.txt", "w") as f:
        f.write(str(val))
    return A / B
