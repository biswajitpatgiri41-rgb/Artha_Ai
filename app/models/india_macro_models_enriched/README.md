# India CPI model retraining with official WPI and RBI credit data

This package adds publicly available **observed** macroeconomic series to the previously trained CPI forecasting suite, runs a same-split feature ablation, and saves retrained ARIMA, Ridge, and XGBoost artifacts. It is an experimental research package—not a production or deployment endorsement.

## What changed

Three official predictor series were captured and kept separate:

| Added series | Observations in raw source | YoY feature coverage | Feature lag |
|---|---:|---|---:|
| OEA all-commodities WPI, 2011–12 base | Apr-2012–Apr-2026 | Apr-2013–Apr-2026 | 1 month |
| OEA all-commodities WPI, 2022–23 base | Apr-2023–Aug-2026 | Apr-2024–Aug-2026 | 1 month |
| RBI DBIE scheduled-bank non-food credit | Jan-2019–Jul-2026 | Jan-2020–Jul-2026 | 2 months |

The WPI bases are **not linked or concatenated**. Each YoY series is calculated within its own base regime. RBI credit is a monthly reporting-date stock in ₹ crore; its YoY rate is calculated from same-source monthly levels. The RBI DBIE table page metadata ended at Jun-2026, but the captured New Format data row contains a reporting date of 31-Jul-2026; this discrepancy is recorded in the source notes.

The previous feature set, CPI target, and model settings are preserved as the **base** variant. Other variants isolate WPI/credit additions: `wpi_old`, `wpi_current`, `credit`, `wpi_old_credit`, `wpi_current_credit`, and `all`.

## Target and evaluation

- **Target:** MoSPI India headline CPI year-over-year percent change, derived from the observed 2024-base CPI index.
- **Real target sample:** 152 monthly observations, Jan-2014–Aug-2026.
- **Test:** expanding rolling-origin evaluation over the same final 24 months, Sep-2024–Aug-2026, for 1-, 3-, and 6-month horizons.
- **No synthetic observations were used.** The separate 10-million-row synthetic scenario collection was excluded from fitting, feature construction, and validation.
- Training inputs are constrained to target values assumed known before each forecast origin. The baseline reproduction check matches the previously delivered metrics to floating-point precision (`results/previous_baseline_reproduction_check.csv`).
- Reported MAE/RMSE are in **percentage points** of CPI YoY.

### Result: new predictors did not yield a consistent improvement

The `all` feature set (both WPI bases plus credit) increased RMSE for both direct models at every horizon in this test:

| Model | Horizon | Base RMSE | All-features RMSE | Change |
|---|---:|---:|---:|---:|
| Ridge | 1 month | 1.437 | 1.845 | +0.408 |
| Ridge | 3 months | 1.950 | 2.218 | +0.269 |
| Ridge | 6 months | 2.294 | 3.310 | +1.016 |
| XGBoost | 1 month | 1.666 | 1.739 | +0.073 |
| XGBoost | 3 months | 1.848 | 1.998 | +0.151 |
| XGBoost | 6 months | 1.963 | 2.012 | +0.049 |

There were isolated, small holdout gains in selected variants—for example, XGBoost with current-base WPI at 1 month (RMSE 1.658 vs 1.666 base) and old-base WPI at 6 months (1.914 vs 1.963). Ridge with credit alone improved at 6 months (2.241 vs 2.294) but worsened at shorter horizons. These are **not reliable proof of improvement**: each horizon has only 24 test cases, and choosing variants after looking at that same holdout creates selection bias.

Among the original reference models, ARIMA(1,0,0) RMSE was 1.219, 1.678, and 2.084 at 1, 3, and 6 months, respectively. At 6 months, base XGBoost scored 1.963. The added predictors do not change the conclusion that these are small-sample prototypes whose out-of-sample performance is uncertain.

See `results/rolling_origin_metrics.csv` and `results/feature_ablation_summary.csv` for complete results.

## Model inventory

- `models/arima_cpi_yoy.pkl`: univariate statsmodels ARIMA(1,0,0) trained on observed CPI YoY only.
- `models/<variant>/ridge_cpi_yoy_h{1,3,6}.json`: final horizon-specific Ridge artifacts.
- `models/<variant>/xgboost_cpi_yoy_h{1,3,6}.json`: final horizon-specific XGBoost boosters.
- Baseline, each single-series ablation, and combined-feature variants are included so experiments can be reproduced. **The `all` variant is not designated as the best model.**
- `results/illustrative_future_forecasts.csv` contains example post-sample forecasts. They are explicitly labeled `target_is_observed=0` and `is_real_world_forecast=0`; they are not actual outcomes or deployment forecasts.

## Inputs and provenance

- `data/source/macro_monthly_available.csv`: actual monthly source panel inherited from the earlier India macro dataset; its target and original predictors are the same as the prior model package.
- `data/raw/`: captured official WPI workbooks and RBI DBIE JSON export.
- `data/processed/`: normalized WPI/credit series and the joined feature panel.
- `source_data_manifest.csv`: source URLs, coverage, units, notes, and SHA-256 hashes.
- `source_research_notes.md`: verification of access and explicit exclusions.

M3 was excluded because the official RBI workbook route returned a human-verification challenge; no bypass was attempted. USD/INR backfill was excluded because an open, documented export route was not verified. An older RBI DBIE credit export that stopped at Dec-2020 was not used; the package uses the public r539 New Format export instead.

## Rebuild and score

Install the pinned dependencies in `requirements.txt`, then run from any directory:

```bash
python scripts/train_enriched_models.py
```

The script reads only the included input panel and raw snapshots. It recreates the normalized CSVs, all rolling metrics, final models, manifests, and illustrative forecasts.

Create an inference CSV with `forecast_origin_month`, `horizon_months`, and the model’s lagged features; run, for example:

```bash
python scripts/score_enriched_models.py \
  --input inference_input.csv \
  --output forecasts.csv \
  --variant all
```

Use `--variant base` to score with the original features. For enriched variants, provide values on the same definitions, units, and lag conventions as the training panel. Missing values are imputed using the stored Ridge training medians; XGBoost handles missing inputs natively.

## Deployment warnings

Do **not** treat these artifacts as ready for real-world deployment. The target history is short, the 24-month test is small, and observed source snapshots do not provide complete historical release vintages. Lag conventions reduce obvious leakage but cannot prove point-in-time availability. WPI values can be provisional, RBI credit is revised and starts only in 2019, and current WPI bases differ. Before deployment, use point-in-time source vintages, a longer untouched prospective test, a monitoring/retraining plan, and a domain review. These models are not financial advice and should not trigger automated policy or trading decisions.
