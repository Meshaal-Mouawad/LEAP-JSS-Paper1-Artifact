# Expected LEAP Result:
# - Governance Status: Validated
# - Review Queue: No
# - Expected Signal(s): None
# - Expected Compliance Rule(s): None
# - Expected Formula Behavior: A / B

# KPI: GDPR Clean Control
# Formula: A / B
# Business Objective: Track operations KPI
# Owner: Enterprise Data Owner
# Source System: SAP PM

def export_data(A, B):
    consent_obtained = True
    data_transfer_agreement = True
    eu_data = "sensitive data"
    export(eu_data)
    return A / B
