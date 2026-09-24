# KPI: Gross Margin Percentage
# Formula: Gross Margin % = (Revenue - Cost) / Revenue * 100
# Description: Percentage of revenue retained after direct production costs.
# Objective: Track financial health and pricing efficiency across product lines.
# Input: Revenue, Cost of Goods Sold
# Unit: %
# Reporting Source: Finance ERP (SAP FI-CO module)
# Used In: CFO Dashboard, Quarterly Financial Review

def calculate_gross_margin_pct(revenue, cost):
    # CONFLICT: business formula specifies (Revenue - Cost) / Revenue * 100
    # but implementation divides revenue by cost instead — operator conflict
    if cost == 0:
        return 0.0
    return (revenue / cost) * 100
