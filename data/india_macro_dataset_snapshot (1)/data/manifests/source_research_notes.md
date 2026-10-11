# Source research and retrieval notes (5 Oct 2026)

## MoSPI CPI 2024-base back series

Official sources: [eSankhyiki CPI page](https://esankhyiki.mospi.gov.in/macroindicators?product=cpi), [CPI FAQ (12 Feb 2026)](https://www.mospi.gov.in/uploads/documents/documents/1770891066052-Annexure_V.pdf), and [January 2026 CPI release](https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf).

MoSPI describes the All-India CPI (General) 2024-base back series for Rural, Urban and Combined as January 2013–December 2024, with annual inflation from January 2014–December 2024. The downloaded eSankhyiki response contains 432 index records (12 years × 12 months × 3 sectors) and 396 y/y observations. The raw pages are preserved in `data/raw/mospi/cpi/mospi_cpi_2024_back_series_all_india_2013_2024.json`. These are joined to the existing Annex-IV 2024-base releases for January 2025–August 2026, giving 164 continuous monthly index observations for each sector. Publisher y/y values and derived index-based y/y changes are kept separate.

The FAQ states that CPI 2012 and CPI 2024 can be linked only at the general-index level because classifications differ. It describes the 2025 annual-average geometric mean factor `LF = Avg(I_new_2025) / Avg(I_old_2025)`, then `I_linked_t = I_old_t × LF`; published factors are Rural 0.5222, Urban 0.5320 and Combined 0.5267. No independently linked values were created here. CPI Food & Beverages and CFPI are distinct concepts and must not be spliced into this 2024-base headline series.

## MoSPI Consumer Food Price Index (CFPI), 2012 base

MoSPI’s official eSankhyiki [Python client/API guide](https://www.mospi.gov.in/esankhyiki-python-library) documents the sequential discovery workflow and CPI API. eSankhyiki CPI metadata identifies group code 7 as **Consumer Food Price** and subgroup `Consumer Food Price-Overall`. The public CPI endpoint `/api/cpi/getCPIIndex` was queried for base year 2012, series Current, All India state code 99, sectors Rural/Urban/Combined, years 2013–2025, and group code 7.

The raw response is preserved in `data/raw/mospi/cfpi/cfpi_2012base_all_india_monthly_2013_2025.json`: 468 monthly index records (156 months × 3 sectors) and 429 publisher-reported y/y rates. The normalized series are separate from the 2024-base CPI and cover January 2013–December 2025. The captured API series does not extend the CFPI index past 2025; newer release y/y may exist separately. This capture does not include CFPI component histories.

## MoSPI Index of Industrial Production (IIP), General monthly index

The official [MoSPI Python client/API guide](https://www.mospi.gov.in/esankhyiki-python-library) lists IIP and documents `get_metadata` followed by `get_data`; the [OpenAPI specification](https://api.mospi.gov.in/layout/swagger_user_iip.yaml) documents `/api/iip/getIIPMonthly`. Public production API requests returned data for `type=General` in two separate base years:

- **2011–12 base:** 168 monthly index observations, April 2012–March 2026, plus the API’s publisher-reported growth rates.
- **2022–23 base:** 41 monthly index observations, April 2023–August 2026, plus publisher-reported growth rates.

Raw paginated responses are saved separately under `data/raw/mospi/iip/`. The two bases overlap from April 2023 to March 2026, but are kept in separate series; no rebasing/linking was performed. Only the General index is included, not sectoral or use-based category histories.

## RBI USD reference-rate archive

Official [RBI Reference Rate Archive](https://www.rbi.org.in/scripts/referenceratearchive.aspx) USD-only export was requested for 1 January 2013–5 October 2026 and preserved as `data/raw/rbi/fx/rbi_usd_reference_rates_2013-01-01_to_2026-10-05.xls`. The response is an HTML table delivered with an Excel-compatible MIME type and `.xls` filename; it is retained as received.

It contains 2,415 available daily observations, earliest 1 January 2013 and latest 5 October 2026. There are no observations from **August 2018 through March 2022**; a separate direct RBI query for 1 January 2019–31 December 2021 returned “No Reference Rate Found.” The 121 available complete-month arithmetic means cover January 2013–July 2018 and April 2022–September 2026. Partial October 2026 is excluded from the monthly mean, while its daily observation remains. This is the RBI reference rate in INR per USD, not a market closing/transaction rate.

## RBI policy rates and remaining gaps

The RBI [Monetary Policy statements archive](https://www.rbi.org.in/scripts/annualpolicy.aspx) records no-change resolutions on **6 February**, **8 April**, **5 June** and **5 August 2026**. Each kept repo at 5.25%, SDF at 5.00%, and MSF/Bank Rate at 5.50%. The linked official resolutions are [February](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62169), [April](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62514), [June](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62863) and [August](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63287); the dated decision log is `data/processed/rbi_mpc_repo_decisions_2026.csv`, and raw HTML pages are under `data/raw/rbi/policy/2026_mpc/`. The RBI current-rates page, as at 13:00 IST on 5 October 2026, reported repo 5.25%, SDF 5.00%, MSF 5.50%, Bank Rate 5.50%, fixed reverse repo 3.35%, CRR 3.00%, SLR 18.00% and INR/USD 96.2831. The one-row normalized capture is `data/processed/rbi_current_rates_snapshot_2026-10-05.csv`, with raw page `data/raw/rbi/policy/rbi_current_rates_snapshot_2026-10-05.html`; the page attributes displayed exchange rates to FBIL. RBI scheduled the October MPC meeting for 5–7 October, so it had not concluded at the snapshot time; no October decision is claimed. The no-change decision log and current snapshot are separate from the historical Table 40 rate-change event history.

RBI FX is USD-only; other RBI FX, reserves, money, credit, WPI, yields, liquidity and external-account series remain unavailable in this package. IMD rainfall normals/departures remain unavailable; the observed rainfall anomaly is derived and labeled. The latest NAS press-note PDF is included but not parsed into quarterly observations.

## Model-training caveat

The CPI target history is long enough for cautious baselines and time-ordered validation, while CFPI and IIP provide useful separate context series. Historical CPI publication lags and revision vintages are not reconstructed; align values to actual release dates before claiming real-time forecast performance. Use a walk-forward/rolling-origin split rather than random partitioning.
