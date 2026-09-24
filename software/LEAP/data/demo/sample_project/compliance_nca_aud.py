# KPI: Inventory Modification Gap
# Description: Detects raw database write activities.
# Unit: count

def write_inventory_log(item_id: str, quantity: int):
    # Violation: missing audit signatures
    db.execute(f"UPDATE inventory SET qty = {quantity} WHERE id = '{item_id}'")
