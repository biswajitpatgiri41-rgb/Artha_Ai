# Training inputs embedded in this package

`raw/` contains the exact 13 source files used by the lean baseline, OECD sensitivity suite, and expanded-feature experiment. The broader dataset archive is delivered separately; this is the smaller, reproducible model-training subset.

## CPI targets

- `raw/mospi/cpi_2024_back_series.csv`
- `raw/mospi/cpi_2024_current_all_india_detailed.csv`

Official MoSPI e-Sankhyiki 2024-base series. Filter to All India, Combined, CPI (General). Use source YoY where present; derive the 12 missing 2025 rates from same-base index levels because the detailed current file does not supply those rates. Do not splice 2012-base CPI levels into this target.

- `raw/oecd/india_monthly_cpi_yoy.csv`

OECD monthly India CPI YoY, used only as a separate long-history sensitivity target.

## Lean external predictors

- `raw/fred/DCOILBRENTEU.csv` — Brent crude benchmark
- `raw/fred/DEXINUS.csv` — INR per USD
- `raw/fred/CPIAUCSL.csv` — U.S. headline CPI
- `raw/fred/FEDFUNDS.csv` — effective U.S. Federal Funds rate

The lean forecast feature panel shifts external variables one month. FRED input filenames retain the series identifiers for attribution.

## Additional expanded-suite predictors

- `raw/fred/DCOILWTICO.csv` — WTI crude benchmark
- `raw/fred/CPILFESL.csv` — U.S. core CPI
- `raw/fred/DTWEXBGS.csv` — broad U.S. dollar index
- `raw/fred/DGS10.csv` — U.S. 10-year Treasury daily yield, averaged monthly
- `raw/world_bank/pink_sheet_monthly_commodity_prices.xlsx` — Pink Sheet monthly indices; Food, Energy, and Fertilizers indexes are converted to YoY changes and shifted one month. These are global commodity benchmarks, not Indian retail prices.
- `raw/wpi/wpi_2011_12_monthly_from_2012.xls` — official Office of the Economic Adviser monthly WPI; All Commodities and IV Food Index are converted to YoY changes and shifted four months. The workbook ends 2026-04.

The expanded feature suite is retained as an experiment because the larger feature block did not outperform the lean ensemble at 1, 3, and 6 months on the shared comparison period, although it had slightly lower 12-month ensemble MAE. Consult `../MODEL_VALIDATION.md` for the measured results and test-set selection caveat.

Official CPI catalogue: <https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?product=CPI>. OECD SDMX source and all source notes are recorded in the parent data archive. Follow each provider's attribution and reuse terms; the presence of a downloaded source file is not a blanket redistribution license.
