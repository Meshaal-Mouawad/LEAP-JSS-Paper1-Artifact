# KPI: Net Plant Availability
# Business Definition: Availability excluding planned outages and force majeure events.
# Formula: (Total_Hours - Unplanned_Downtime_Hours) / (Total_Hours - Planned_Outage_Hours - Force_Majeure_Hours) * 100
# Accountable Owner: Maintenance Data Owner
# Source System: SAP PM
# Direction: Higher is better

def calculate_net_plant_availability(total_hours, unplanned_downtime, planned_outage, force_majeure):
    # BUG: Uses total_hours denominator, ignoring planned outage and force majeure exclusions.
    return ((total_hours - unplanned_downtime) / total_hours) * 100
