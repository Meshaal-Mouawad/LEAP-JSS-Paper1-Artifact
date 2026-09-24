# KPI: Daily Feedstock Throughput (tons/day)
# Formula: \mathrm{Throughput} = \frac{\mathrm{Total\ Feedstock\ (tons)}}{\mathrm{Hours\ Online}} \times 24
def calculate_demo_throughput(
    total_feedstock_tons: float, hours_online: float
) -> float:
    # KPI: Daily Feedstock Throughput (tons/day)
    if hours_online == 0:
        return 0.0
    throughput = (total_feedstock_tons / hours_online) * 24
    return throughput
