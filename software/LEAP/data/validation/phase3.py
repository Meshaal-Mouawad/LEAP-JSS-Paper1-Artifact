# file: kpi_utilization.py


def calculate_utilization(actual_production_time, planned_operation_time):
    """
    Asset Utilization KPI
    ISO-22400 compliant
    """
    return actual_production_time / planned_operation_time
