# KPI: EU Data Export Volume
# Description: Tracks volume of cross-border transfers.
# Unit: GB

def export_eu_data(dataset: list):
    # Violation: cross_border transfer of personal_data
    send_to_foreign_server(dataset)
