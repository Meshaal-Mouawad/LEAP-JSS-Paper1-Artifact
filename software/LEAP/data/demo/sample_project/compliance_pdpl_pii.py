# KPI: Customer Activity Index
# Description: Measures customer interactions containing raw customer data.
# Unit: index

def calculate_activity(national_id: str, phone_num: str):
    # Violation: raw ID and phone used directly
    print(f"Processing customer: {national_id} / {phone_num}")
    return 1.0
