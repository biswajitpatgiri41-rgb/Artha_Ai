# India Macro Dataset Snapshot

**Snapshot date:** 5 October 2026 (retrieval timestamps are stored in UTC in the manifests)  
**Status:** useful, source-cited partial collection — **not the complete production dataset in the attached requirements**.

## Summary

The package contains **54,008 canonical observations across 34 series**, plus immutable raw source files, normalized extracts, SHA-256 provenance, validation reports, and reproducible local normalization scripts. It includes long-run IMD rainfall, daily and monthly Brent, FRED series, IMF/WDI annual context, a short current-base MoSPI CPI series, and RBI policy-rate events.

Several highest-priority India series remain unavailable in this snapshot: complete historical CPI/CFPI, IIP, parsed GDP/GVA, RBI exchange rates, M3, credit, WPI, government yields, FX reserves, external accounts, and official rainfall departures. Consequently, **this is not yet a ready-to-train CPI forecasting panel** and no forecast targets were fabricated.

## Download / file guide

- `data/processed/macro_observations.csv` — canonical long-format observations; includes `obs_date`, `series_id`, `value`, `unit`, `frequency`, source and vintage fields, plus `raw_file` and `hash` for each row.
- `data/processed/macro_monthly_available.csv` — sparse monthly feature table. Empty cells are missing observations, not zeros. It does not convert annual/quarterly series to monthly data.
- `data/processed/eia_brent_monthly.csv`, `eia_brent_daily.csv` — parsed EIA Brent series.
- `data/processed/imd_whole_india_monthly_long.csv`, `imd_whole_india_monthly_and_seasonal_wide.csv`, `imd_whole_india_seasonal.csv` — IMD actual rainfall in long, source-shaped wide, and seasonal forms.
- `data/processed/rbi_policy_rate_events.csv` — event-date policy and reserve-requirement rates from RBI Handbook Table 40.
- `data/processed/mospi_cpi_2024base_available_months.csv` — published All-India rural, urban, and combined CPI general indices for the available months in Annex IV.
- `data/processed/mospi_cpi_aug2026_division_snapshot.csv`, `mospi_cpi_aug2026_group_snapshot.csv` — MoSPI August 2026 category/group release snapshots, not historical series.
- `data/raw/` — downloaded publisher files as received; do not edit these files.
- `data/manifests/ingestion_manifest.csv` — raw-file inventory, official URLs, retrieval timestamps, status, byte counts and checksums. Failed RBI download attempts are retained as failed status rows; they are not data.
- `data/manifests/series_catalog.csv` — canonical series coverage, frequency, units, source and raw-file hashes.
- `data/manifests/data_quality_report.json` — validation counts and coverage limitations.
- `scripts/normalize_downloaded.py`, `scripts/finalize_dataset.py` — local-only steps to regenerate normalized extracts, attach hashes, and rebuild derived monthly fields from files already in `data/raw/`.

## Coverage matrix

| Provider / requested area | What is included | Coverage / status |
|---|---|---|
| **MoSPI CPI headline (2024 base)** | Annex I, II and IV August 2026 official Excel annexures; Annex IV parsed to monthly rural/urban/combined index and published y/y rates | Index: Jan 2025–Aug 2026 (20 months); published y/y: Jan–Aug 2026 (8 months). Aug 2026 is provisional; release date 14 Sep 2026. **Historical CPI (including 2012 base), CFPI and full component histories are not included.** |
| **MoSPI CPI groups/components** | Division and group-level index/inflation snapshots from the August 2026 annexures | One release period only; not a continuous component panel. Do not equate CPI food groups with the separate CFPI series. |
| **MoSPI IIP** | Catalogue page verified latest release through Aug 2026 | XLSX URL returned `File not found`; **no IIP observations included**. |
| **MoSPI GDP/GVA** | Official catalogue-linked press-note PDF for Q1 FY 2026–27 (constant- and current-price release) | Raw PDF included; not parsed into quarterly observations. No interpolation or monthly conversion. |
| **RBI policy / reserve rates** | Official RBI Handbook Table 40 workbook; event rows normalized for bank rate, repo, reverse repo, SDF, MSF, CRR and SLR | Event history starts in 1970; each rate’s last event varies, latest through Dec 2025 in this workbook. Other requested RBI series were not downloaded. |
| **RBI macro/financial series** | Failed download attempts and exact source URLs recorded in the manifest | **Missing:** INR/USD, NEER/REER, WPI, M1/M3/reserve money, bank/non-food credit, WACR/liquidity, Indian G-Sec/T-bills, FX reserves, external accounts and parsed fiscal series. RBI file-host TLS connections closed during workbook retrieval; DBIE/UI exports were not available through the open fetch route used here. |
| **EIA Brent (RBRTE)** | Official daily and monthly Europe Brent Spot Price FOB workbooks and parsed CSV | Daily: 20 May 1987–29 Sep 2026 (9,097 observations). Monthly: May 1987–Aug 2026 (472 observations). USD/barrel. |
| **FRED** | FEDFUNDS, CPIAUCSL, DGS10, DGS2, DGS3MO | Fed funds monthly: Jul 1954–Sep 2026; US CPI monthly: Jan 1947–Aug 2026; 10-year yield daily: Jan 1962–Oct 2026; 2-year daily: Jun 1976–Oct 2026; 3-month daily: Sep 1981–Oct 2026. |
| **IMD rainfall** | Whole-India actual monthly and seasonal rainfall | Monthly actual: Jan 1901–Dec 2024 (1,488 observations). **Official rainfall normal/departure series are not included.** A separate derived monthly anomaly is actual rainfall minus the 1991–2020 calendar-month mean, explicitly labeled as derived—not as an official IMD departure. |
| **IMF global context** | DataMapper annual real GDP growth and average CPI inflation for India, World, advanced economies and emerging/developing economies | WEO April 2026 vintage; 1980–2031 where provided. The source includes forecast years; distinguish them from historical values before any backtest. |
| **World Bank context** | WDI GDP growth, CPI inflation and trade (% GDP) for India and World | Annual, available observations mainly 1960–2025; gaps/nulls are not filled. |

A machine-readable mapping is in `data/manifests/coverage_matrix.csv`.

## Derived fields and alignment rules

- CPI index levels remain explicitly tagged as **2024 base**; no 2012-base index has been concatenated or rebased.
- `oil_yoy` and `us_cpi_yoy` are calculated as 100 × 12-month percentage change from the corresponding monthly series.
- Daily US yields are retained daily in the canonical store and separately aggregated to monthly arithmetic means, named `*_monthly_average`. `us_yield_curve_10y_minus_2y` is the difference of those monthly means.
- RBI policy rates are represented in the monthly table at month-end by the last effective event available by that month-end. The table stops at the last source event; rates are not projected beyond the source history. `repo_change_1m` and `repo_change_3m` are percentage-point differences.
- `month_sin` and `month_cos` are deterministic calendar features.
- Annual IMF/WDI series are not upsampled. Missing values are not set to zero, and no CPI or macro series is blindly forward-filled.
- No `target_h1`, `target_h3`, `target_h6`, `target_h12`, lag, or rolling CPI forecast features were generated: the continuous Indian headline CPI target history needed to validate them is missing.

## Validation and provenance

- Canonical observation key: `(obs_date, series_id, frequency, geography)`; duplicate keys are checked and none remain in this snapshot.
- Numeric observations link to the exact raw snapshot path and SHA-256 checksum; the raw-file inventory provides independent checksums and download status.
- Original source frequencies, units, source URLs and IMF/WDI vintage fields are retained where available.
- The monthly wide table is intentionally **sparse** and is not a promise that every variable spans every date.
- Source release timestamps are not available historically for all providers. A production real-time/backtest dataset still needs release-date/vintage histories to prevent look-ahead leakage.

## Rebuilding derived files

From the package root, with Python and the listed common libraries installed:

```bash
python3 scripts/normalize_downloaded.py
python3 scripts/finalize_dataset.py
```

These scripts perform local transformations only; they do not bypass MoSPI registration/token requirements or the RBI download issue. Raw files remain unchanged.

## Remaining access needed for full specification

To produce the complete requested platform dataset, the missing official exports/API access must be obtained for MoSPI historical CPI/CFPI/IIP and GDP/GVA tables, and RBI DBIE/Handbook data for FX, money, credit, WPI, yields, reserves, liquidity and external/fiscal series. IMD official normals/departures are also still needed. The open snapshots here should be treated as a verified partial data collection, not a substitute for those series.
