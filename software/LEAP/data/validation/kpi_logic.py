# Case C (Mismatch)
def yield_rate(scrap_units, total_units):
    return scrap_units / total_units  # WRONG definition vs documentation


# Case D (Both)
def profit_margin(revenue, cost):
    return revenue - cost  # Missing division → mismatch


# Case E (Equivalent)
def production_yield(good, total):
    return good / total  # same logic as SQL → should PASS
