# India CPI source and reconciliation notes

## Kaggle and official CPI archive

The selected Kaggle dataset is [All India Consumer Price Index (2013–2023)](https://www.kaggle.com/datasets/yatharthgupta18/all-india-consumer-price-index20132023). The listing attributes the data to MoSPI via data.gov.in, describes Rural, Urban and Rural+Urban sectors, 26 categories plus General CPI, 2012=100, and the Government Open Data License—India. The public dataset API archive SHA-256 is `586ed80b16185822b6f48132449881b47f34ee4b434d0b6db63cdf33acbc50b3`.

The Kaggle page claims data through October 2023, but the downloaded CSV actually ends May 2023 for Rural and Urban and April 2023 for Rural+Urban. It contains 371 sector-month rows. The first-party [MoSPI/data.gov.in CPI archive through August 2025](https://www.data.gov.in/resource/all-india-consumer-price-index-ruralurban-upto-august-2025) is available at [this direct CSV URL](https://www.data.gov.in/files/ogdpv2dms/s3fs-public/All_India_Index_Upto_Aug25.csv), SHA-256 `8fc14c9029d51c6baa5ca946282d10b1d7bf3b8817923e1020748384415bd520`. On all 371 overlapping sector-month rows and 27 measurements, all 10,017 cells match exactly, including missingness.

The archive omits the April 2019 sector-month row. Both sources also have General-index blanks in April and May 2020. These source gaps are retained, not interpolated. Kaggle public API downloads are supported without account authentication according to [Kaggle staff](https://www.kaggle.com/product-announcements/485439); no credential was read or created and no connector setting changed.

## Final official target series and vintage difference

MoSPI’s [December 2025 CPI release](https://www.mospi.gov.in/uploads/latestReleases/latest_release_1768213461321_53cd35fd-1bbc-4b43-b92d-8fb67474ee74_Press_Release_of_CPI_for_December_2025.pdf) includes Annexure VI, the 2012-base All-India General CPI index from January 2013 through December 2025, and Annexure VII, published year-over-year inflation from January 2014 through December 2025. The published-rate table marks April and May 2020 with dashes. The model label is this directly published MoSPI YoY series: 142 observed target values, with no fill or interpolation. Published rates agree with rates derived from the same release’s one-decimal index within 0.005 percentage points.

The final MoSPI index differs from the older archived Combined General index in 10 of 149 nonmissing, calendar-aligned overlaps, by up to 2.1 index points. The final published YoY series differs from YoY derived from the archived Combined General index in 135 overlapping months (mean absolute difference about 0.11 percentage points; maximum about 1.46 pp; 19 months differ by more than 0.02 pp). The package preserves both vintages and uses the later official published YoY series as the target rather than silently blending historical values. Kaggle/data.gov.in category and sector indices remain model features with source periods and ending dates recorded.

The [February 2026 MoSPI release](https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf) finalizes December 2025 at base 2012=100: Combined General CPI index 198.0 and YoY inflation 1.33%, matching the time-series table endpoint. MoSPI introduced a new 2024=100 series in February 2026. This package stops at December 2025 and does not mix the new base into the old-base training target; it is not yet a model for the current 2024-base series.

The separate `NMDS2.0_CPI_Excel.xlsx` file was CPI metadata documentation, not a time-series dataset, and is not model input. An initial guessed data.gov.in file path returned HTML and was discarded; only the verified direct CSV above is used.
