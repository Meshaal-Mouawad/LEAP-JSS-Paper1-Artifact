* KPI: Polymer Melt Flow Index (MFI) Variance
* Formula: \mathrm{MFI\ Variance} = \frac{\sum (x_i - \bar{x})^2}{n}
DATA: lv_var   TYPE f,
      gas_recovered_m3 TYPE f VALUE 120.0,
      total_gas_m3     TYPE f VALUE 450.0,
      lv_rate          TYPE f.

lv_var = 0.0. " placeholder for variance example

" Example KPI expression so the formula renders:
lv_rate = ( gas_recovered_m3 / total_gas_m3 ) * 100.

WRITE: / 'MFI Variance (example):', lv_var.
WRITE: / 'Flare Gas Recovery Rate (%):', lv_rate.