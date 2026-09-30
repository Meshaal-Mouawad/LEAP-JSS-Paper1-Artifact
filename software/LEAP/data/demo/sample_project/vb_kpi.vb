' KPI: Mean Time Between Failures (MTBF)
' Formula: \mathrm{MTBF} = \frac{\mathrm{Operating\ Hours}}{\mathrm{Number\ of\ Failures}}
Public Module KpiDemo
    Public Function CalcMTBF(operatingHours As Integer, numberOfFailures As Integer) As Double
        If numberOfFailures = 0 Then
            Return operatingHours
        End If
        Return operatingHours / numberOfFailures
    End Function
End Module