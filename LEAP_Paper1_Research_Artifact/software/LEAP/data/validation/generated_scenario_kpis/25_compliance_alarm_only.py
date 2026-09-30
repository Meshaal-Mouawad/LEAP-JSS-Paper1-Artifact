# Expected LEAP Result:
# - Governance Status: Needs Review
# - Review Queue: Yes
# - Expected Signal(s): Compliance Risk
# - Expected Compliance Rule(s): GDPR-DATA-PROC-01
# - Expected Formula Behavior: A / B

# KPI: GDPR Alarm Only
# Formula: A / B
# Business Objective: Track operations KPI
# Owner: Enterprise Data Owner
# Source System: SAP PM

def export_data(A, B):
    eu_data = "sensitive data"
    export(eu_data)
    return A / B
