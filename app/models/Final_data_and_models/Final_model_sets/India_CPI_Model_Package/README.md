# India CPI Forecast Model Suite

This package contains trained numerical forecast models and a reproducible workflow for **monthly India CPI Combined, General Group year-over-year inflation**. The principal target uses MoSPI's 2024-base back/current series. It also includes an independent OECD long-history sensitivity run and an expanded-feature MoSPI experiment.

## Model families included

- Seasonal Naive benchmark
- ETS
- ARIMA and seasonal ARIMA (SARIMA)
- SARIMAX with lagged external regressors
- VAR (the expanded suite restricts its VAR to a compact, project-relevant subset)
- Direct-horizon XGBoost at 1, 3, 6, and 12 months
- Development-weighted ensemble

The suite also creates empirical prediction intervals, seeded residual-bootstrap summaries, XGBoost gain/SHAP explanations when available, a Taylor-rule reference, local-projection associations with HAC errors, input-quality checks, and a drift watch. The HMM is an **exploratory full-sample smoothed retrospective diagnostic**, not a real-time regime probability. The bootstrap is historical residual resampling—not a structural shock/scenario model.

## Target, data, and feature suites

The primary MoSPI target has **152 monthly observations, 2014-01 through 2026-08**. MoSPI provides the 2024-base YoY value for 140 observations; for 2025, the 12 missing YoY observations are derived from the same-base current and prior-year index levels. Those index values are rounded to one decimal, which limits precision. No 2012-base and 2024-base CPI **levels** are spliced.

Two MoSPI model specifications are saved separately:

1. **Lean baseline — `artifacts/mospi_2024_base/`:** CPI history/lags plus four monthly macro predictors (Brent, INR/USD, U.S. headline CPI, and effective Federal Funds rate); external values are shifted one month. In SARIMAX, the last available lagged external vector is held constant through each forecast horizon.
2. **Expanded-feature experiment — `artifacts/mospi_2024_base_extended/`:** the same target and backtest design, with 13 monthly predictors: baseline predictors plus WTI, U.S. core CPI, broad dollar index, U.S. 10-year yield, World Bank Pink Sheet food/energy/fertilizer indexes, and official 2011–12-base WPI All Commodities and Food Index inflation. Pink Sheet controls are shifted one month; WPI is shifted four months as a conservative release-delay safeguard. The source WPI workbook ends 2026-04.

The OECD sensitivity series has **440 monthly YoY observations, 1990-01 through 2026-08**. It is fitted as a separate target; it is not spliced into or averaged with MoSPI.

### Dataset coverage choices

The model ZIP carries the raw input files used by these fits. The wider source archive contains additional datasets, but not every file is a valid monthly real-time CPI predictor. The following were excluded from the trained input matrix rather than silently imputed or mislabeled:

- **India food CPI:** available files cross the 2012/2024 CPI-base transition and do not provide one continuous, vintage-consistent 2024-base food predictor over the training/test window. Food-price proxies in the expanded suite are WPI and global commodity benchmarks, not Indian retail food CPI.
- **IIP:** the available OECD/FRED India industrial-production alternative ends 2023-01, before the 2024-01–2026-08 comparison period. It was not carried forward into current months.
- **RBI repo:** exact dated monthly history was not retrieved. The OECD/FRED central-bank-rate proxy ends 2023-12 and is not guaranteed to equal RBI repo; the separate RBI landing-page snapshot has no effective date. Neither is treated as a repo history.
- **Weather:** the high-resolution IMD grids and regional summary end in 2024 and lack 2025–26 coverage for the comparison period.
- **Annual WDI/IMF WEO:** low-frequency annual observations and (for WEO) projection values do not form point-in-time monthly features for this model.
- **PMI/UPI:** licensed PMI history and the public UPI mirror export were not retrieved as downloadable series. UPI would in any case be a payment-activity proxy, not direct CPI/consumption.

The full source archive/catalog and its provenance notes are delivered separately. This package preserves the exact subset used to reproduce these trained artifacts.

## Validation design and important selection caveat

The pipeline uses expanding-window monthly rolling-origin forecasts—no random shuffle. Origins before 2024-01 form the development set; forecasts with target months 2024-01 through 2026-08 form the **comparison period**. Development forecasts alone determine each suite's ensemble weights and empirical interval widths. There are 32 overlapping forecast errors per horizon, so results are dependent and the sample is modest.

**The comparison period is no longer an untouched final holdout.** After examining the first suite, an expanded predictor specification was fitted and both specifications were compared on the same 2024–2026 outcomes. Treat the following scores as comparative evidence, not an unbiased final performance claim. A new prospective set of issued forecasts—or a new genuinely unseen release window—is required before any production decision.

## Results: MoSPI baseline and expanded specification

Errors are mean absolute error (MAE) in percentage points (pp). Smaller is better. `Best component` is the lowest raw comparison-period MAE among the individual models plus ensemble; it is descriptive and was not used to refit test forecasts.

| Horizon | Baseline ensemble MAE | Expanded ensemble MAE | Seasonal-naive MAE | Baseline best component | Expanded best component |
|---:|---:|---:|---:|---|---|
| 1 month | 0.385 | 0.438 | 1.787 | SARIMAX 0.358 | SARIMAX 0.431 |
| 3 months | 0.819 | 0.959 | 1.787 | SARIMAX 0.767 | SARIMA 0.884 |
| 6 months | 1.147 | 1.357 | 1.787 | Ensemble 1.147 | SARIMAX 1.242 |
| 12 months | 1.515 | 1.463 | 1.787 | XGBoost 1.189 | XGBoost 1.312 |

The expanded suite was worse on ensemble MAE at 1/3/6 months, and modestly better at 12 months. The baseline's 12-month XGBoost score was lower than either 12-month ensemble. The feature expansion is retained as an experiment; it is **not** presumed to improve accuracy merely because it has more predictors.

Baseline ensemble empirical interval coverage on the same comparison period was 93.8%, 81.3%, 65.6%, and 68.8% for nominal 80% intervals at 1/3/6/12 months; corresponding nominal 95% coverage was 100%, 100%, 84.4%, and 75.0%. The expanded suite also under-covered at 6 and 12 months. These intervals are historical-error bands, not guaranteed confidence intervals.

## Stored forecast snapshot

Latest bundled target observation is 2026-08. The following are the **lean-baseline ensemble** forecasts; horizons refer to months ahead from that origin.

| Target month | Horizon | YoY point forecast | Empirical 80% interval |
|---|---:|---:|---:|
| 2026-09 | 1 month | 4.69% | 3.84%–5.54% |
| 2026-11 | 3 months | 4.67% | 3.41%–5.94% |
| 2027-02 | 6 months | 4.41% | 2.91%–5.90% |
| 2027-08 | 12 months | 4.38% | 2.63%–6.13% |

These are saved forecasts from the training-time origin, **not live refreshed predictions**. The separate expanded-suite and OECD-sensitivity forecasts are in their own `forecasts.csv` files.

## Other project-roadmap items

- **Nowcasting:** no separate nowcast was fitted; the latest bundled target is 2026-08, and there is no point-in-time higher-frequency release panel.
- **Regimes:** the two-state Gaussian HMM is retrospective and uses full-sample smoothed probabilities; its past probabilities see later observations and must not be used as real-time signals.
- **Local projections:** exploratory conditional associations only, not causal impulse responses.
- **Taylor rule:** an explicit-parameter reference, not an RBI recommendation.
- **Monte Carlo:** empirical residual bootstrap only; no structural shock distribution was identified.
- **Counterfactuals/policy optimization:** not fitted because no causal identification strategy, validated welfare/loss function, or policy constraints were supplied.
- **LLM agents:** Planner/Data/Inflation/Growth/External/Econometrics/Policy/Critic/Report agents from the notes are research/orchestration components, not numerical forecast models, and are not trained or deployed by this package.

## Production caveats

This is a reproducible research package, **not a production certification**. The official-base target history is short, the 2025 target is index-derived, historical point-in-time release vintages are unavailable, and the post-2024 comparison period has been used for feature-specification comparison. Prediction-interval coverage—especially at longer horizons—is below nominal. Before operational use, obtain dated RBI repo and current IIP/food predictors, preserve release vintages, issue forecasts prospectively without looking ahead, create a new untouched evaluation window, monitor data and residual drift, set retraining/rollback rules, and require human review.

## Reproduce and inspect

Python 3.11+ is recommended. From this directory:

```bash
python -m pip install -r requirements.txt
python train_models.py --data data --out artifacts
python train_extended_models.py --data data --out artifacts/mospi_2024_base_extended
python predict.py --registry artifacts/mospi_2024_base/models/model_registry.joblib
```

`train_models.py` rebuilds the lean MoSPI and OECD sensitivity suites; `train_extended_models.py` rebuilds the expanded MoSPI suite. These commands overwrite their output folders. `predict.py` reads stored forecasts; it does **not** ingest new CPI observations or refit models.

Key files:

- `artifacts/mospi_2024_base/models/` — saved component models and registry for the lean primary suite.
- `artifacts/mospi_2024_base/backtest_predictions.csv`, `test_metrics.csv`, `forecasts.csv` — rolling-origin records, scorecard, and latest snapshot.
- `artifacts/mospi_2024_base_extended/` — expanded-feature models, inputs, backtest, scorecard, forecasts, and source checksums.
- `artifacts/oecd_long_history_sensitivity/` — separate OECD target models and artifacts.
- `MODEL_VALIDATION.md` — detailed fit, feature, validation, and results audit.
- `data/raw/` — the raw inputs embedded for reproducibility; baseline hashes are in `artifacts/source_data_checksums.json`, and expanded-suite hashes are in `artifacts/mospi_2024_base_extended/source_data_checksums.json`.

Source attribution/reuse terms remain those of each provider; local retrieval does not imply blanket redistribution rights. See the full dataset archive's source notes for URLs and access caveats.
