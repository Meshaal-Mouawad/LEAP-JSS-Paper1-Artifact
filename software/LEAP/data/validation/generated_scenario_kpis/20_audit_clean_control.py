# Expected LEAP Result:
# - Governance Status: Validated
# - Review Queue: No
# - Expected Signal(s): None
# - Expected Compliance Rule(s): None
# - Expected Formula Behavior: A / B

# KPI: Audit Clean Control
# Formula: A / B
# Business Objective: Track operations KPI
# Owner: Enterprise Data Owner
# Source System: SAP PM

def modify_value(val, A, B):
    actor = "admin"
    timestamp = "2026-07-12"
    before = 10
    after = A / B
    diff = after - before
    with open("audit.txt", "w") as f:
        f.write(f"{actor} {timestamp} {before} {after} {diff}")
    return after
