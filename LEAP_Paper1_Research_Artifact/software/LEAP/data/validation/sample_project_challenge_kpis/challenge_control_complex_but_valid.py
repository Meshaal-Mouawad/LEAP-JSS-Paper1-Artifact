# KPI: Adjusted Feedstock Yield
# Business Definition: Measures good product yield after excluding approved rework and non-prime product.
# Formula: Good_Product_Tons / (Feedstock_Tons - Approved_Rework_Tons - NonPrime_Tons) * 100
# Accountable Owner: Operations Data Owner
# Source System: MES
# Direction: Higher is better

def calculate_adjusted_feedstock_yield(good_product_tons, feedstock_tons, approved_rework_tons, nonprime_tons):
    denominator = feedstock_tons - approved_rework_tons - nonprime_tons
    return (good_product_tons / denominator) * 100
