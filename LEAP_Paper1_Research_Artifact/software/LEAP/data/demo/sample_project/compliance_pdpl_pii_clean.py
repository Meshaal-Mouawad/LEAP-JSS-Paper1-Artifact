# KPI: Masked Customer Activity Index
# Description: Measures customer interactions.
# Unit: index

def calculate_activity_clean(national_id: str, phone_num: str):
    # Safe: uses masking
    masked_id = mask(national_id)
    return 1.0
