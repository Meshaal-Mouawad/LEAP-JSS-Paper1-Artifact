// KPI: Cooling Water Delta-T (°C)
public static class CoolingWater
{
    public static double DeltaT(double inlet_c, double outlet_c)
    {
        // ΔT = outlet - inlet
        return outlet_c - inlet_c;
    }
}