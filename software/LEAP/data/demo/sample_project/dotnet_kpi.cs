// KPI: Propylene to Ethylene (P/E) Ratio
public static class KpiDemo
{
    public static double ComputePERatio(double propyleneProducedTons, double ethyleneProducedTons)
    {
        if (ethyleneProducedTons == 0) return 0.0;
        return propyleneProducedTons / ethyleneProducedTons;
    }
}