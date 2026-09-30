# KPI: Audit Trail Completeness
# Description: Evaluates lineage tracking records.
# Unit: %

def evaluate_lineage(trace_records: list):
    # Violation: trace records are unsigned
    return len(trace_records)
