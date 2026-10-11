# Normalization report — India monthly CPI

The training target is MoSPI's **published All-India General CPI year-over-year inflation rate** on the 2012=100 series. Its source table covers January 2014–December 2025 with 142 published observations; the Ministry marks April and May 2020 with dashes. The last 2012-base value was finalized in February 2026. The published rates agree with the final table's one-decimal index-derived rates within 0.0050 percentage points. No target is filled or interpolated.

The Kaggle listing describes January 2013–October 2023, but the downloaded CSV actually ends 2023-05 for Rural, 2023-05 for Urban, and 2023-04 for Rural+Urban. The Kaggle snapshot contains 371 rows. The first-party August 2025 data.gov.in snapshot contains 453 sector-month rows. All 10,017 overlapping measurement cells match exactly, including missingness. Kaggle and the official archive are retained as CPI category and sector feature inputs.

MoSPI's final December 2025 2012-base General CPI index table differs from the older archived Combined General index in 10 of 149 nonmissing overlapping values, with a maximum difference of 2.1 index points. The directly published target differs from YoY calculated from the older archive in 135 overlapping months (MAE 0.11 pp; maximum 1.46 pp). The package therefore uses the final published YoY series as the target, preserves the archived series separately, and records the vintage break.

Category-level inputs from the Kaggle/data.gov.in snapshots end in August 2025. MoSPI introduced the new 2024=100 CPI in February 2026; no 2024-base observations are mixed into this package. The backtest is a prototype, not a production-readiness certification. All raw-file hashes are recorded in `source_manifest.json`.

## Sources

[1] [Kaggle India CPI dataset](https://www.kaggle.com/datasets/yatharthgupta18/all-india-consumer-price-index20132023)
[2] [MoSPI/data.gov.in CPI archive through August 2025](https://www.data.gov.in/resource/all-india-consumer-price-index-ruralurban-upto-august-2025)
[3] [MoSPI December 2025 CPI release and Annexures VI–VII](https://www.mospi.gov.in/uploads/latestReleases/latest_release_1768213461321_53cd35fd-1bbc-4b43-b92d-8fb67474ee74_Press_Release_of_CPI_for_December_2025.pdf)
[4] [MoSPI February 2026 release finalizing December 2025 at 2012=100](https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf)
