# India Macro Dataset Snapshot

**Snapshot date:** 5 October 2026 (retrieval times and SHA-256 provenance are recorded in the manifests)  
**Status:** substantial, source-cited model-training collection; still a **partial** capture of the original source wish-list.

## What is included

The canonical long table contains **58,686 observations across 46 series**, with no duplicate canonical keys. The sparse monthly feature file has 1,510 rows; annual observations remain annual rather than being upsampled.

- **MoSPI CPI (2024 base):** All-India General index, Combined/Rural/Urban, January 2013–August 2026 (164 continuous monthly observations per sector); official y/y values and index-derived y/y changes remain separate.
- **MoSPI CFPI (2012 base):** Consumer Food Price-Overall index, All-India Combined/Rural/Urban, January 2013–December 2025 (468 index values) plus 429 publisher-reported y/y rates. This is a separate old-base series, not a continuation of the 2024-base headline CPI.
- **MoSPI IIP General:** 2011–12 base, April 2012–March 2026 (168 index observations); and 2022–23 base, April 2023–August 2026 (41 index observations). Official publisher growth rates are separate features. The two base regimes are not linked or spliced.
- **RBI USD reference rate:** 2,415 available daily INR/USD observations, January 2013–5 October 2026, plus 121 observed complete-month arithmetic means. The source has no observations from August 2018 through March 2022; missing months are not imputed.
- **RBI 2026 MPC decisions:** official no-change decisions on 6 February, 8 April, 5 June and 5 August; the repo remained 5.25%, SDF 5.00%, and MSF/Bank Rate 5.50%. A separate one-row current-rate snapshot is dated 5 October 2026 at 13:00 IST. The scheduled October 5–7 MPC meeting had not concluded at that time.
- Existing EIA Brent, FRED, IMF, World Bank, IMD rainfall, RBI policy-event, CPI annexure and national-accounts source files remain included.

This supports cautious baselines and time-ordered evaluation, but is **not point-in-time backtest-ready**. Historical CPI publication lags and revisions were not reconstructed. Align every feature to the date it became available, and use walk-forward/rolling-origin validation rather than random splits.

## Download / file guide

- `data/processed/macro_observations.csv` — canonical long-format observations with `obs_date`, `series_id`, value, unit, native frequency, source and vintage fields, and exact `raw_file`/SHA-256 links.
- `data/processed/macro_monthly_available.csv` — sparse monthly feature table. Empty cells are missing, not zero. It includes separate CPI/CFPI/IIP series, `usd_inr_monthly_average`, and explicitly derived y/y and other features. It does not upsample annual series.
- `data/processed/mospi_cpi_2024base_all_india_monthly.csv` — joined 2024-base Combined/Rural/Urban index history, official y/y where published, source-regime and release-snapshot flags, and derived index-based y/y.
- `data/processed/mospi_cpi_2024base_available_months.csv` — backward-compatible wide CPI file, January 2013–August 2026; official y/y fields are `combined_yoy`, `rural_yoy`, and `urban_yoy`.
- `data/processed/mospi_cfpi_2012base_all_india_monthly.csv` — 2012-base CFPI index and official y/y values by month and sector.
- `data/processed/mospi_iip_general_monthly_by_base.csv` — IIP General index and growth values in separate 2011–12 and 2022–23 base columns.
- `data/processed/rbi_usd_inr_reference_rate_daily.csv` and `rbi_usd_inr_monthly_average.csv` — daily source observations and derived complete-month means. No absent month is filled; partial October 2026 is excluded from the monthly mean.
- `data/processed/rbi_policy_rate_events.csv` — event-date bank, repo, reverse-repo, SDF, MSF, CRR and SLR history from RBI Handbook Table 40.
- `data/processed/rbi_mpc_repo_decisions_2026.csv` — four official 2026 no-change MPC decisions, with source links and corresponding raw HTML.
- `data/processed/rbi_current_rates_snapshot_2026-10-05.csv` — one-date current policy and selected FX snapshot; its quoted exchange-rate source is FBIL. Not an historical series.
- `data/raw/` — unmodified publisher downloads/API responses, including page-level MoSPI API data and RBI release HTML; preserve these snapshots.
- `data/manifests/ingestion_manifest.csv` — raw-file inventory, source URLs, retrieval timestamps, statuses, bytes and checksums.
- `data/manifests/series_catalog.csv` — canonical series coverage, frequency, units, geography and raw-source hash.
- `data/manifests/coverage_matrix.csv` — requested-series coverage and limitations.
- `data/manifests/data_quality_report.json` — validation totals and training-readiness cautions.
- `data/manifests/source_research_notes.md` — official-source methods, access routes and retrieval notes.

## Coverage and important gaps

| Provider / area | Included | Coverage / status | Important limitations |
|---|---|---|---|
| **MoSPI headline CPI, 2024 base** | All-India General index, Combined/Rural/Urban; official y/y where published | Index: Jan 2013–Aug 2026 (164 months per sector) | Back-series vintage differs from the current-release snapshot. No continuous division/group/item history. Do not splice CFPI into headline CPI. |
| **MoSPI CFPI, 2012 base** | Consumer Food Price-Overall index and official y/y, Combined/Rural/Urban | Jan 2013–Dec 2025 | Separate from 2024-base CPI; no CFPI index after Dec 2025 or component-level histories in this capture. |
| **MoSPI IIP** | General index and publisher growth in two separate base regimes | 2011–12 base: Apr 2012–Mar 2026; 2022–23 base: Apr 2023–Aug 2026 | No linking/splicing across bases. Sectoral, manufacturing-subsector and use-based panels are not included. |
| **MoSPI GDP/GVA** | Official Q1 FY 2026–27 NAS press-note PDF | Raw PDF included | Not parsed into quarterly observations; no interpolation or monthly conversion. |
| **RBI reference-rate FX** | USD-only INR-per-USD daily series and observed-month means | 2,415 daily points, Jan 2013–5 Oct 2026; 121 observed monthly means | **Source gap:** no observations Aug 2018–Mar 2022. The RBI reference rate is not a market close/transaction rate. |
| **RBI policy / reserve rates** | Historical event rows, 2026 MPC decision log and separate current-rate snapshot | Table 40 rate-change history through Dec 2025; no-change MPC decisions through Aug 5; snapshot as of Oct 5 13:00 IST | October 5–7 MPC meeting was still in progress at snapshot time; no post-meeting decision is claimed. The decision log is not an effective-rate event history and the snapshot does not backfill monthly rates. Other RBI variables remain missing. |
| **EIA Brent (RBRTE)** | Official daily and monthly Europe Brent Spot Price FOB workbooks and parsed CSV | Daily: 20 May 1987–29 Sep 2026; monthly: May 1987–Aug 2026 | USD/barrel; source frequencies retained. |
| **FRED** | FEDFUNDS, CPIAUCSL, DGS10, DGS2, DGS3MO | Long historical monthly/daily spans | U.S. series are context, not substitutes for Indian observations. |
| **IMD rainfall** | Whole-India actual monthly and seasonal rainfall | Jan 1901–Dec 2024 | Official rainfall normals/departures are not included. A separately labeled anomaly uses the 1991–2020 calendar-month mean. |
| **IMF / World Bank** | Annual GDP growth, CPI inflation, trade and related context | Vintages/years vary by indicator | Annual stays annual; IMF rows can include forecasts through 2031. Never repeat them as monthly observations. |

## Base-year and training cautions

- CPI index levels are tagged `2024=100`; the historical rows are the official 2024-base back series, and the newer rows come from Annex-IV release snapshots. Publisher y/y values and index-derived 12-month changes are separate.
- CFPI is the 2012-base Consumer Food Price-Overall series. CPI Food & Beverages is a different classification. Do not treat it as CFPI or combine the 2012-base CFPI index with the 2024-base CPI.
- MoSPI documents a linking method for the headline general index only. No independent linking factors or rebased CFPI/IIP values were calculated here.
- IIP 2011–12 and 2022–23 base values overlap, but the package intentionally keeps them as separate columns and canonical IDs.
- Treat MPC no-change decisions as dated policy announcements, not rate-change events; the Table 40 event file and 2026 decision log have different semantics. The October 5 current-rate page predates the scheduled October MPC conclusion.
- Do not treat monthly observations as known on the first day of their reference month. Historical publication timestamps and point-in-time revisions are not fully available. Use release-date/vintage alignment for real-time backtests.
- FX monthly means use only available daily RBI reference rates within each observed calendar month. Missing months stay missing.

## Validation and provenance

- Canonical observation key: `(obs_date, series_id, frequency, geography)`; duplicate keys are checked and none remain.
- Every canonical row links to a source snapshot path and SHA-256; unmapped source rows are checked by the finalizer.
- Native frequency, units, base year, source URL and vintage are retained where available.
- Missing values are not converted to zero and series are not blindly forward-filled.
- Monthly features derived from index levels are explicitly labeled; annual/quarterly series are not upsampled.

## Rebuilding derived files

From the package root, install `scripts/requirements.txt`. With the included raw files, run:

```bash
python3 scripts/normalize_downloaded.py
python3 scripts/extend_training_series.py
python3 scripts/fetch_rbi_mpc_decisions_2026.py --from-raw
python3 scripts/capture_rbi_current_snapshot.py --from-raw
```

The first script rebuilds the original downloaded series. The extension script consumes the included CPI back-series, CFPI, IIP and RBI archive raw data, updates manifests and normalized panels, then invokes `finalize_dataset.py`. The two `--from-raw` commands rebuild RBI’s separate decision log and current snapshot without network access. To refresh MoSPI data, run `python3 scripts/fetch_mospi_cfpi_iip.py`; to refresh RBI MPC pages/snapshot, run `python3 scripts/fetch_rbi_mpc_decisions_2026.py` and `python3 scripts/capture_rbi_current_snapshot.py` without `--from-raw`. These refresh commands require network access. Raw files are preserved as retrieved.

## Remaining priorities

A richer production dataset still needs extended RBI DBIE series for WPI, bank credit/money, yields, liquidity, reserves, external accounts and effective exchange rates; additional India-specific FRED/RBI policy history; MoSPI CPI component back histories; IIP sectoral and use-based categories; and IMD official rainfall normals/departures. Consider this a useful but partial macroeconomic training collection, not a complete feature panel.
