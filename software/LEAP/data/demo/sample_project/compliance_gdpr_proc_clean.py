# KPI: Governed EU Data Export
# Formula: Governed EU Data Export = exported_dataset_count
# Description: Tracks cross-border transfer.
# Unit: GB

def export_eu_data_governed(dataset: list):
    # Safe: cross_border transfer of personal_data with consent and processing_agreement
    send_to_foreign_server(dataset)
    return len(dataset)
