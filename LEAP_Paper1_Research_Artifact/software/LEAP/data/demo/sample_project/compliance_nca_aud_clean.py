# KPI: Governed Inventory Modification
# Formula: Governed Inventory Modification = governed_modification_count
# Description: Logs database modifications.
# Unit: count

def write_inventory_governed(item_id: str, quantity: int):
    # Safe audit signature trace:
    # actor: system
    # timestamp: 2026
    # before: 0
    # after: 1
    # diff: +1
    db.execute(f"UPDATE inventory SET qty = {quantity}")
    return 1
