# Expected LEAP Result:
# - Governance Status: Needs Review
# - Review Queue: Yes
# - Expected Signal(s): Compliance Conflict
# - Expected Compliance Rule(s): KSA-PDPL-REG-01
# - Expected Formula Behavior: A / B

# KPI: PDPL PII Violation
# Formula: A / B
# Business Objective: Track operations KPI
# Owner: Enterprise Data Owner
# Source System: SAP PM

def get_data(national_id, phone_num, employee_record, A, B):
    # Triggers PDPL rule since PII fields exist
    val = A / B
    return national_id, phone_num, employee_record, val
