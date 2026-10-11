The best learned candidate is **ARIMA(1,0,0)**, with pooled rolling-origin MAE of **0.990 percentage points across 275 forecasts**. It does not pass every horizon gate. The lowest-MAE strategy was ARIMA for one month, Persistence for three months, and ARIMA for six months.

The model target is MoSPI’s directly published All-India General CPI year-over-year rate on the 2012=100 base, with 142 observed labels through December 2025. The Kaggle CPI category/sector archive is retained as feature data. MoSPI’s later final release revises some historical values, so the target uses the later published YoY series and the older Kaggle/data.gov.in vintage is kept separate. [1] [2] [3] [4]

## Rolling-origin results

Monthly expanding-window origins start with January 2018 forecast issues. Each origin uses data dated no later than the last observed month `s`; horizon `h` predicts the target for `s+h`. Forecast samples are 94, 92, and 89 observations for the 1-, 3-, and 6-month horizons. MAE skill is `1 − model MAE / Persistence MAE` on matched target cases. A positive skill beats Persistence; the prototype threshold is at least 60 forecasts and skill ≥ 0. These are internal screening gates, not official or regulatory standards.

| Model | Horizon | Forecasts / 60 minimum | MAE (pp) | Persistence MAE (pp) | Skill / 0 minimum | Decision |
|---|---:|---:|---:|---:|---:|---|
| ARIMA(1,0,0) | 1 month | 94 / 60 | 0.572 | 0.572 | 0.001 / 0.000 | Pass, near tie |
| Persistence | 1 month | 94 / 60 | 0.572 | 0.572 | 0.000 / 0.000 | Pass |
| Ridge | 1 month | 94 / 60 | 0.636 | 0.572 | -0.111 / 0.000 | Fail |
| Seasonal Naive | 1 month | 92 / 60 | 1.883 | 0.548 | -2.435 / 0.000 | Fail |
| XGBoost | 1 month | 94 / 60 | 0.733 | 0.572 | -0.280 / 0.000 | Fail |
| ARIMA(1,0,0) | 3 months | 92 / 60 | 1.097 | 1.096 | -0.001 / 0.000 | Fail |
| Persistence | 3 months | 92 / 60 | 1.096 | 1.096 | 0.000 / 0.000 | Pass |
| Ridge | 3 months | 92 / 60 | 1.347 | 1.096 | -0.229 / 0.000 | Fail |
| Seasonal Naive | 3 months | 90 / 60 | 1.895 | 1.104 | -0.716 / 0.000 | Fail |
| XGBoost | 3 months | 92 / 60 | 1.298 | 1.096 | -0.184 / 0.000 | Fail |
| ARIMA(1,0,0) | 6 months | 89 / 60 | 1.322 | 1.389 | 0.048 / 0.000 | Pass |
| Persistence | 6 months | 89 / 60 | 1.389 | 1.389 | 0.000 / 0.000 | Pass |
| Ridge | 6 months | 89 / 60 | 1.672 | 1.389 | -0.204 / 0.000 | Fail |
| Seasonal Naive | 6 months | 87 / 60 | 1.907 | 1.375 | -0.387 / 0.000 | Fail |
| XGBoost | 6 months | 89 / 60 | 1.376 | 1.389 | 0.009 / 0.000 | Pass, marginal |

The Seasonal Naive benchmark is unavailable for two target cases per horizon because its year-earlier published target is missing; its Persistence comparison is therefore calculated on the matched subset. Full RMSE, bias, median absolute error, benchmark skills, and threshold fields are in `metrics_by_model_horizon.csv` and `threshold_scorecard.csv`.

## Interpretation

ARIMA’s one-month result is essentially tied with Persistence, and its three-month result is marginally worse. Its six-month MAE is about 4.8% below Persistence. XGBoost’s six-month gain is under 1%; Ridge is worse than Persistence at every horizon. Treat ARIMA as the best learned prototype artifact, not as a proven operational advantage.

This is not a “perfect” or production-certified model. The old 2012-base CPI series ends in December 2025; MoSPI introduced a 2024=100 series in February 2026. The model must be retrained and revalidated on the new-base observations before being used for current inflation forecasts. Historical release timestamps for the Kaggle/data.gov.in category features are unavailable, so publication-lag leakage cannot be ruled out. [2] [4]

## References

[1]: https://www.mospi.gov.in/uploads/latestReleases/latest_release_1768213461321_53cd35fd-1bbc-4b43-b92d-8fb67474ee74_Press_Release_of_CPI_for_December_2025.pdf "MoSPI: CPI release for December 2025, Annexures VI–VII"
[2]: https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf "MoSPI: January 2026 CPI release finalizing December 2025 at base 2012=100"
[3]: https://www.kaggle.com/datasets/yatharthgupta18/all-india-consumer-price-index20132023 "Kaggle: All India Consumer Price Index (2013–2023)"
[4]: https://www.data.gov.in/resource/all-india-consumer-price-index-ruralurban-upto-august-2025 "MoSPI/data.gov.in: All India CPI through August 2025"
