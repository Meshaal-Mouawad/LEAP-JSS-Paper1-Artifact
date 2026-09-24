# KPI: Compressor Vibration Index
# Formula: Vibration Index = Peak Vibration Amplitude / Baseline Threshold
# Description: Normalized vibration severity for rotating compressor units.
# Objective: Early detection of mechanical degradation before catastrophic failure.
# Input: Peak vibration (mm/s), Baseline safe threshold (mm/s)
# Unit: dimensionless ratio
# Reporting Source: OSIsoft PI System (Historian)
# Used In: Reliability Dashboard, Predictive Maintenance Alert System

# Threshold conflict: A higher Vibration Index means MORE vibration relative to baseline —
# meaning higher is WORSE (indicates machine degradation approaching failure).
# However, the logic below treats higher values as BETTER (returns 'GOOD' for high values),
# inverting the business interpretation of this KPI.

def calculate_vibration_index(peak_vibration_mm_s: float, baseline_threshold_mm_s: float) -> float:
    if baseline_threshold_mm_s <= 0:
        return 0.0
    index = peak_vibration_mm_s / baseline_threshold_mm_s

    # CONFLICT: threshold interpretation is inverted.
    # Business: index > 1.0 means threshold EXCEEDED — bad condition.
    # Code below labels high index as GOOD performance — directly contradicts business rule.
    if index >= 1.0:
        status = "GOOD_PERFORMANCE"   # BUG: should be ALERT or CRITICAL
    else:
        status = "BELOW_THRESHOLD"    # BUG: this is actually the SAFE state
    return index
