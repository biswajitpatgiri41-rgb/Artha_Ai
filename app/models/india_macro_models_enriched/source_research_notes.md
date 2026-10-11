# Official macro-data enrichment: verified sources and exclusions

Research and retrieval snapshot: 5 October 2026. All added inputs are observed public-source data. The separate synthetic scenario files were not used for fitting or evaluation.

## Series added for the retraining experiment

| Series | First-party source and retrieved file | Verified content | Model use and caveat |
|---|---|---|---|
| All-commodities WPI, 2011–12 base | Office of the Economic Adviser (OEA), [public monthly workbook](https://eaindustry.nic.in/indx_download_1112/monthly_index_202606.xls), captured as `wpi_2011_12_monthly_202606.xls` | Monthly index levels Apr-2012–Apr-2026; YoY growth is computed within the same base. | Used as a lagged predictor. The workbook flags recent months as provisional; it is a current snapshot, not a release-vintage archive. |
| All-commodities WPI, 2022–23 base | OEA, [public monthly workbook](https://eaindustry.nic.in/indx_download_2223/wpi_monthly_index_202609.xlsx), captured as `wpi_2022_23_monthly_202609.xlsx` | Index levels Apr-2023–Aug-2026; same-base YoY growth is available Apr-2024 onward. | Kept as a distinct lagged predictor. It is never spliced to the 2011–12 base; recent values may be provisional and historical values are not first-release vintages. |
| Scheduled-bank non-food credit | RBI DBIE, [official table page](https://dbie.rbihub.in/tables?table=financial_sector.r539_deployment_of_bank_credit_by_major_sectors); current-format export captured as `rbi_credit_new_format.json` from the table's visible New Format option. | 91 monthly reporting dates, Jan-2019–Jul-2026, with non-food credit levels in rupees crore. The page metadata says through Jun-2026, while the downloaded New Format row contains a 31-Jul-2026 date; that difference is recorded rather than silently hidden. | YoY growth computed from the levels and lagged two months. The series is provisional/revisable; dates are reporting dates and do not guarantee availability at every backtest cutoff. |

The DBIE table's public New Format file is `539--deployment-of-bank-credit-by-major-sectors--new-format.csv`; the exact JSON export URL used is `https://data-api.dbie.rbihub.in/api/tables/financial_sector/r539_deployment_of_bank_credit_by_major_sectors/rows?src_file=539--deployment-of-bank-credit-by-major-sectors--new-format.csv`. The older r766 source file initially probed was not used: it ended in Dec-2020 in the downloaded payload, despite a broad `full-history` label. The current r539 New Format export is the source actually added to training.

## Checked, not added

- **M3:** the official RBI Table 165 workbook route returned a human-verification challenge in this environment. Following the user's confirmation, it was not bypassed, solved, or used.
- **USD/INR:** RBI/FBIL provide public archive interfaces, but FBIL historical export requires registration and email OTP, and no open documented API was verified. The prior dataset's gap was not filled from an unverified route.
- **2012-base CPI:** a MoSPI historical CPI release was reviewed. It overlaps the current 2024-base target history and does not add target months to this model; CPI bases are not silently mixed.
- **Rainfall:** IMD's Whole India monthly series was verified through Dec-2024, with no 2025–2026 national monthly rows. It therefore did not add recent training inputs beyond the inherited panel.

## Modeling and validation

WPI and non-food credit can only add lagged predictors for the CPI target; they create no new CPI labels. The target remains the observed MoSPI 2024-base headline CPI YoY series (Jan-2014–Aug-2026). Models are compared across the same 24-month Sep-2024–Aug-2026 expanding rolling-origin test, and the baseline feature set is reproduced for a like-for-like check. Source release dates and historical vintages are unavailable, so one-/two-month lags are safeguards, not proof of point-in-time availability. Any holdout improvement is exploratory, based on 24 test cases per horizon, and not evidence of real-world deployment performance.
