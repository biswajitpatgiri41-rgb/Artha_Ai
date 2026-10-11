# Performance summary

**Verdict:** the newly collected real-world predictors did not produce a consistent improvement on the fixed Sep-2024–Aug-2026 rolling test. The baseline reproduction check is exact to floating-point precision, so comparisons use the same target, folds, and model settings as the earlier suite.

## All features versus original feature set

RMSE is in percentage points of CPI YoY; lower is better. Each value is based on 24 rolling-origin test cases.

| Model | Horizon | Original features | Both WPI bases + RBI credit | Difference |
|---|---:|---:|---:|---:|
| Ridge | 1 | 1.437 | 1.845 | +0.408 |
| Ridge | 3 | 1.950 | 2.218 | +0.269 |
| Ridge | 6 | 2.294 | 3.310 | +1.016 |
| XGBoost | 1 | 1.666 | 1.739 | +0.073 |
| XGBoost | 3 | 1.848 | 1.998 | +0.151 |
| XGBoost | 6 | 1.963 | 2.012 | +0.049 |

## Isolated feature gains

- XGBoost + 2022–23-base WPI at 1 month: RMSE 1.658 vs 1.666 baseline (a small 0.008 pp reduction).
- XGBoost + 2011–12-base WPI at 6 months: RMSE 1.914 vs 1.963 baseline (0.049 pp reduction).
- Ridge + credit only at 6 months: RMSE 2.241 vs 2.294 baseline (0.053 pp reduction); its 1- and 3-month scores were worse.
- No feature addition beat the baseline for both direct model families across all three horizons.

The holdout was not used to select a recommended winner; selecting among many variants on these same 24 cases would overfit the reported test. Full results are in `rolling_origin_metrics.csv` and `feature_ablation_summary.csv`. This experiment does not establish real-world deployment performance.
