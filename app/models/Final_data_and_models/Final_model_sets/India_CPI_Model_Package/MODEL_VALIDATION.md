# Model training and validation report

**Project:** India monthly CPI Combined, General Group YoY forecasting  
**Run date:** 2026-10-09  
**Data origin:** latest official MoSPI target month 2026-08  
**Units:** target and forecasts are inflation percent; errors are percentage points (pp)

## Executive result

All seven requested numerical forecast families were fitted and serialized: Seasonal Naive, ETS, ARIMA, SARIMA, SARIMAX, VAR, and direct-horizon XGBoost. A non-negative ensemble was fitted using development-only rolling-origin performance weights. A separate 440-month OECD sensitivity suite and a 13-exogenous-variable MoSPI feature experiment are also bundled.

For the lean MoSPI specification, comparison-period ensemble MAE was 0.385, 0.819, 1.147, and 1.515 pp at 1/3/6/12 months, versus 1.787 pp for Seasonal Naive at all horizons. The wider feature set improved the ensemble at 12 months slightly, but worsened it at 1/3/6 months; it does not dominate the lean model. The best single component by raw comparison-period MAE was SARIMAX at 1/3 months, ensemble at 6 months, and baseline XGBoost at 12 months.

**Do not interpret these as production-grade performance guarantees.** The official target history has only 152 monthly observations; the comparison period has 32 overlapping forecasts per horizon. After the initial model run, an expanded feature specification was compared on the same 2024-01–2026-08 outcomes. That period is therefore **not an untouched final holdout**, and feature-set selection may create optimism. A prospective evaluation must be collected without tuning on its outcomes.

## Data and target audit

- Target: official MoSPI/NSO India CPI Combined, General Group, YoY; 2024-base back/current files; 152 monthly values from 2014-01 to 2026-08.
- 140 YoY values are directly present. Twelve 2025 values are derived from same-base monthly index levels because the detailed current file omits the YoY field; one-decimal index precision limits these derived values.
- No CPI index levels from 2012 and 2024 bases were concatenated.
- Lean baseline uses lagged Brent YoY, INR/USD YoY, US headline CPI YoY, and Federal Funds rate plus autoregressive/seasonal model terms.
- Expanded feature suite has 13 predictors: the four lean controls plus WTI YoY, US core CPI YoY, broad USD index YoY, US 10-year Treasury average, World Bank Pink Sheet Food/Energy/Fertilizer index YoY, and official WPI All Commodities/Food Index YoY. WPI is lagged four months; other external series are lagged one month. A documented one-month US CPI/core-CPI carry-forward gap occurs at source month 2025-10.
- OECD long-history target is its own monthly India CPI YoY series, 440 values from 1990-01 to 2026-08; its levels, definition, and vintage are not blended with MoSPI.

## Fit and backtest design

- Monthly expanding-window rolling origins; no random split. Origins are refit using only target history available at the origin.
- Development forecasts (targets before 2024-01) determine ensemble weights and each model's empirical error intervals. The comparison period targets 2024-01 through 2026-08.
- There are 32 overlapping forecast errors per horizon; they are correlated, and the effective information content is smaller than 32 independent observations.
- The same comparison targets were subsequently used to compare lean versus expanded features. These scores are comparative, not an untouched final test.
- All seven model families serialized in both MoSPI suites with no final-fit component errors recorded. `model_registry.joblib` in each suite is the inference entry point. Each XGBoost horizon is stored separately.

## MoSPI comparison scorecards

### Lean baseline

| Horizon | Ensemble MAE | Ensemble RMSE | Seasonal Naive MAE | Lowest raw MAE model | 80% coverage | 95% coverage |
|---:|---:|---:|---|---|---:|---:|
| 1 month | 0.385 | 0.478 | 1.787 | SARIMAX 0.358 | 93.8% | 100.0% |
| 3 months | 0.819 | 0.978 | 1.787 | SARIMAX 0.767 | 81.3% | 100.0% |
| 6 months | 1.147 | 1.427 | 1.787 | Ensemble 1.147 | 65.6% | 84.4% |
| 12 months | 1.515 | 1.936 | 1.787 | XGBoost 1.189 | 68.8% | 75.0% |

### Expanded feature experiment

| Horizon | Ensemble MAE | Ensemble RMSE | Seasonal Naive MAE | Lowest raw MAE model | 80% coverage | 95% coverage |
|---:|---:|---:|---|---|---:|---:|
| 1 month | 0.438 | 0.563 | 1.787 | SARIMAX 0.431 | 87.5% | 100.0% |
| 3 months | 0.959 | 1.147 | 1.787 | SARIMA 0.884 | 96.9% | 100.0% |
| 6 months | 1.357 | 1.597 | 1.787 | SARIMAX 1.242 | 75.0% | 81.3% |
| 12 months | 1.463 | 1.909 | 1.787 | XGBoost 1.312 | 71.9% | 78.1% |

The expanded-feature ensemble MAE is about 13.7%, 17.1%, and 18.3% higher at 1/3/6 months than the lean ensemble, and about 3.4% lower at 12 months. The lean direct XGBoost's 12-month MAE (1.189 pp) is also lower than the expanded direct XGBoost (1.312 pp). The expanded experiment is retained for audit/research, not declared the overall winner.

### Interval reliability

Intervals are empirical development-error quantiles, not parametric confidence intervals or guaranteed prediction sets. The lean ensemble's 80% coverage drops to 65.6% at six months and 68.8% at twelve months; its 95% coverage is 84.4% and 75.0% at those horizons. The expanded suite has similarly weak long-horizon 95% coverage (81.3% at six months; 78.1% at twelve months). Recalibration and prospective coverage monitoring are required; the current intervals should not be used as calibrated risk limits.

## Stored MoSPI forecast snapshot

Origin 2026-08; lean-baseline ensemble:

| Horizon | Target month | Point forecast | Empirical 80% band | Empirical 95% band |
|---:|---|---:|---:|---:|
| 1 month | 2026-09 | 4.689% | 3.840%–5.538% | 2.572%–6.806% |
| 3 months | 2026-11 | 4.674% | 3.406%–5.942% | 2.366%–6.982% |
| 6 months | 2027-02 | 4.408% | 2.912%–5.903% | 2.200%–6.615% |
| 12 months | 2027-08 | 4.380% | 2.630%–6.130% | 2.080%–6.680% |

Forecasts are stored in each suite's `forecasts.csv`; component forecasts and ensemble weights are embedded as JSON columns. `predict.py` prints the saved forecast—it does not fetch or assimilate newer data.

## OECD sensitivity results

The long-history alternative improves on its own seasonal-naive MAE at 1, 3, and 6 months (ensemble MAE 0.283, 0.566, 1.020 pp; seasonal-naive 1.507 pp), but **loses** to its seasonal-naive baseline at 12 months (1.647 vs 1.507 pp). It is a different target/vintage and remains separate from the official forecast.

## Project methods delivered versus deferred

- **Delivered:** fitted forecast families, rolling-origin predictions, learned ensemble weights, empirical interval calibration, XGBoost gain importance/SHAP when available, descriptive two-state HMM, seeded empirical residual bootstrap, deterministic Taylor reference, exploratory local projections with HAC errors, data-quality checks, and a drift watch.
- **Not a live nowcast:** no dated high-frequency inputs and the target already runs through 2026-08. Saved forecasts start at 2026-09.
- **Regime limitation:** HMM states are full-sample smoothed retrospective probabilities; they use later observations to classify earlier months and are not valid real-time signals. No independent regime validation was performed.
- **Causal/policy limitation:** local-projection estimates are associations; the Taylor rule is a reference calculation, not RBI advice. No historical counterfactual or policy optimization was trained because no identification strategy, policy loss function, and constraints were supplied.
- **Monte Carlo limitation:** the seeded bootstrap resamples historical forecast residuals; it is not a structural scenario simulation and does not assign causal shock probabilities.
- **Agents:** Planner/Data/Inflation/Growth/External/Econometrics/Policy/Critic/Report agents are orchestration/research components in the notes; they are not trained numerical forecasts and are not included as LLM agents in this model artifact.

## Candidate data not used as model predictors

The source bundle includes more material than can responsibly be forced into a 152-month, monthly point-in-time feature matrix:

- MoSPI CPI food/group files use the 2012 base through 2025, whereas the main target is 2024-base; available back series is general-only, so food was not spliced across bases.
- The downloaded OECD/FRED India IIP proxy ends 2023-01; the RBI central-bank-rate proxy ends 2023-12 and is not guaranteed to be repo. An RBI rate snapshot has no stated effective date. No dated official repo history was available in the bundle.
- IMD rainfall files stop at 2024; annual WDI and projected WEO tables are too low-frequency or non-realized for the monthly real-time fit; licensed PMI and the UPI mirror bulk file were unavailable.
- The expanded suite adds available WPI and global commodity series as interpretable proxies, but those do not replace Indian CPI food, current IIP, or an event-dated RBI repo series.

## Recommended production path

1. Obtain dated MoSPI first-release/vintage files, current official IIP, a stable 2024-base food series, and event-dated RBI repo history; preserve the source release timestamps.
2. Treat the currently inspected 2024–2026 period as development/comparison, then issue frozen forecasts prospectively. Do not tune on those future outcomes.
3. Compare with the seasonal-naive benchmark, record every forecast origin/prediction, and report uncertainty/calibration by horizon and regime.
4. Require a genuinely new untouched evaluation window, monitoring thresholds, alerting/retraining/rollback controls, reproducible environment hashes, and human sign-off before deployment.

This deliverable is a reproducible research model package, not a guarantee of future accuracy or a certification of production readiness.
