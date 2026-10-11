# India CPI Forecasting — Dataset Package

Generated: 2026-10-08T14:53:56.288040+00:00

This package is a source-labelled research dataset bundle for the attached India CPI forecasting workflow. It contains real public-source observations and provider files only—no synthetic data. The companion PDF explains the project requirements, source decisions, modeling use, and gaps.

## Bundle snapshot

- Raw source files: **51**
- Total raw-data size: **60.58 MiB**
- MoSPI CPI rows: 15,150 (2012-base group history), 42,159 (2012-base item panel), 432 (2024-base back series), and 40,080 (2024-base current detailed all-India panel).
- World Bank WDI panel: **612150 rows**, 35 of 36 requested indicators retrieved after retry.
- IMD regional rainfall: 620 rows (124 annual rows × 5 regions); daily 0.25-degree grid files: **13 annual files**, limited to CPI-era years and listed individually in the IMD manifest.

Exact paths, byte sizes, checksums, and tabular row counts are in `metadata/FILE_INVENTORY.csv` and `metadata/PACKAGE_MANIFEST.json`.

## Folders

- `raw/` — original CSV, CSV.GZ, XLS/XLSX, HTML source captures, and annual NetCDF rainfall files (gzip-compressed).
- `metadata/DATASET_CATALOG.csv` — every major dataset family named in the workflow, with local paths, source, status, and caveats.
- `metadata/download_manifest.json` — collector results, source URLs, and observation counts.
- `metadata/wdi_retry_manifest.json` — retries and recovered WDI indicators.
- `metadata/FILE_INVENTORY.csv` — SHA-256 inventory for raw files.
- `source_notes/VERIFIED_SOURCES.md` — official links, alternatives, coverage, and access/licensing caveats.
- `report/main.pdf` — the accompanying project/dataset analysis report.
- `download_bundle.py`, `download_imd_grid.py`, `repair_wdi.py`, `build_catalog.py` — reproducible acquisition and inventory scripts.

## Most important files

- `raw/mospi/cpi_2012_all_india_group_history.csv` — official 2012-base CPI group history.
- `raw/mospi/cpi_2012_item_history.csv` — official 2012-base CPI item observations.
- `raw/mospi/cpi_2024_current_all_india_detailed.csv` and `raw/mospi/cpi_2024_back_series.csv` — separate 2024-base current/back-series files.
- `raw/world_bank/wdi_selected_all_countries_long.csv.gz` — all-country annual WDI panel.
- `raw/imf/WEOApr2026all.xlsx` — IMF April 2026 WEO workbook.
- `raw/world_bank/pink_sheet_monthly_commodity_prices.xlsx` — monthly global commodity panel.
- `raw/eia/brent_daily_official.xls` — official EIA daily Brent; WTI is stored separately.
- `raw/wpi/wpi_2011_12_monthly_from_2012.xls` — official monthly OEA WPI.
- `raw/imd/imd_regional_monthly_seasonal_rainfall_1901_2024.csv` — official long-history five-region rainfall summary.

## Critical limitations and safe use

1. **CPI bases stay separate.** Preserve 2012-base and 2024-base files as different vintages; do not splice levels without an official method. Compute YoY consistently within each base.
2. **The repo-rate gap is explicit.** `raw/fred/IRSTCB01INM156N_india_central_bank_rate.csv` is the OECD/FRED *central-bank-rate proxy* (monthly through Dec-2023), not a guaranteed event-dated RBI repo history. `raw/rbi/dbie_landing_snapshot.csv` is a retrieval-date-only snapshot. Replace both with official RBI event history for final modeling.
3. **IIP is a proxy in this package.** `INDPROINDMISMEI` is an OECD/FRED India industrial-production alternative, not current MoSPI release-vintage IIP.
4. **PMI was not retrieved.** It is licensed; use official IIP as an open activity feature. UPI is not household consumption; the mirror export was not downloaded.
5. **Frequency and release timing matter.** WDI and WEO are annual; EIA/FRED market data are daily; CPI and OECD indices are monthly; policy changes are event-dated. Aligning series to a month does not remove release lags.
6. **Rainfall grids need spatial aggregation.** The annual NetCDF files contain grid data, not a ready monthly India-average feature. Apply India/crop-region masks and aggregate explicitly. The regional table provides long history for quick baselines.
7. **Data vintages prevent look-ahead leakage.** Store `ref_month` and source release/vintage date separately. Backtests must use only data available at the forecast origin.
8. **Re-use terms are source-specific.** Public retrieval is not a blanket license to redistribute. Retain provider attribution and review terms, especially FRED/OECD and the IMF/World Bank workbooks.

## Re-running / updating

From this folder, with Python 3 and `requests`, `pandas`, and `beautifulsoup4` available:

```bash
python3 download_bundle.py
python3 repair_wdi.py
IMD_GRID_START=2012 IMD_GRID_END=2024 IMD_GRID_WORKERS=3 python3 download_imd_grid.py
python3 build_catalog.py
```

The download scripts may take time and network access; they skip synthetic values and log failures. Check each manifest before modeling.
