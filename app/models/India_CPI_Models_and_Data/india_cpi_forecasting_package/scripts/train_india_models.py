#!/usr/bin/env python3
"""Train and evaluate direct monthly India CPI forecasts.

Target: MoSPI-published All-India CPI General YoY inflation, 2012=100 series.
Forecast origin is the last observed month s; an h-month model predicts y[s+h]
using features dated no later than s. Backtests expand monthly through time.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import statsmodels
import xgboost
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data/processed/india_cpi_monthly_panel.csv"
TARGET_PATH = ROOT / "data/processed/india_headline_cpi_target.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from india_feature_engineering import TARGET_COL, build_feature_frame, load_panel  # noqa: E402

HORIZONS = [1, 3, 6]
BACKTEST_FIRST_ISSUE = pd.Period("2018-01", freq="M")
MIN_TRAINING_SAMPLES = 36
MIN_ARIMA_OBSERVATIONS = 36
THRESHOLD_MIN_FORECASTS = 60


def make_ridge() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=8.0)),
    ])


def make_xgboost() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("model", XGBRegressor(
            objective="reg:squarederror",
            n_estimators=100,
            max_depth=2,
            learning_rate=0.04,
            min_child_weight=3,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=8.0,
            reg_alpha=0.0,
            random_state=2026,
            n_jobs=1,
            tree_method="hist",
        )),
    ])


def fit_direct_model(family: str, x: pd.DataFrame, y: pd.Series):
    estimator = make_ridge() if family == "Ridge" else make_xgboost()
    estimator.fit(x, y)
    return estimator


def dump_pickle(value: Any, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest}


def as_json_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Period):
        return str(value)
    if isinstance(value, dict):
        return {str(k): as_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [as_json_value(v) for v in value]
    return value


def fit_arima(history: pd.Series):
    observed = history.dropna()
    if len(observed) < MIN_ARIMA_OBSERVATIONS:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", UserWarning)
        return ARIMA(history.astype(float), order=(1, 0, 0), trend="c").fit()


def evaluate_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (model, horizon), group in predictions.groupby(["model", "horizon_months"], sort=False):
        actual = group["actual_yoy_pct"].to_numpy(dtype=float)
        forecast = group["forecast_yoy_pct"].to_numpy(dtype=float)
        error = forecast - actual
        persistence = predictions[
            (predictions["model"] == "Persistence") & (predictions["horizon_months"] == horizon)
        ][["origin_month", "target_month", "forecast_yoy_pct"]].rename(
            columns={"forecast_yoy_pct": "persistence_forecast"}
        )
        seasonal = predictions[
            (predictions["model"] == "SeasonalNaive") & (predictions["horizon_months"] == horizon)
        ][["origin_month", "target_month", "forecast_yoy_pct"]].rename(
            columns={"forecast_yoy_pct": "seasonal_naive_forecast"}
        )
        paired = group.merge(persistence, on=["origin_month", "target_month"], how="inner")
        paired_seasonal = group.merge(seasonal, on=["origin_month", "target_month"], how="inner")
        mae = float(mean_absolute_error(actual, forecast))
        rmse = float(np.sqrt(mean_squared_error(actual, forecast)))
        bias = float(np.mean(error))
        p_mae = float(mean_absolute_error(paired["actual_yoy_pct"], paired["persistence_forecast"])) if len(paired) else np.nan
        s_mae = float(mean_absolute_error(paired_seasonal["actual_yoy_pct"], paired_seasonal["seasonal_naive_forecast"])) if len(paired_seasonal) else np.nan
        skill_p = 1.0 - mae / p_mae if np.isfinite(p_mae) and p_mae > 0 else np.nan
        skill_s = 1.0 - float(mean_absolute_error(paired_seasonal["actual_yoy_pct"], paired_seasonal["forecast_yoy_pct"])) / s_mae if len(paired_seasonal) and np.isfinite(s_mae) and s_mae > 0 else np.nan
        rows.append({
            "model": model,
            "horizon_months": int(horizon),
            "n_forecasts": int(len(group)),
            "mae_pp": mae,
            "rmse_pp": rmse,
            "median_absolute_error_pp": float(median_absolute_error(actual, forecast)),
            "bias_pp_forecast_minus_actual": bias,
            "persistence_mae_on_paired_cases_pp": p_mae,
            "seasonal_naive_mae_on_paired_cases_pp": s_mae,
            "mae_skill_vs_persistence": float(skill_p) if np.isfinite(skill_p) else np.nan,
            "mae_skill_vs_seasonal_naive": float(skill_s) if np.isfinite(skill_s) else np.nan,
            "first_target_month": str(group["target_month"].min()),
            "last_target_month": str(group["target_month"].max()),
        })
    return pd.DataFrame(rows).sort_values(["horizon_months", "model"]).reset_index(drop=True)


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel(str(PANEL_PATH))
    target_frame = pd.read_csv(TARGET_PATH)
    y = panel[TARGET_COL].astype(float)
    features = build_feature_frame(panel)
    latest_target_month = y.dropna().index.max()
    calendar_end = panel.index.max()
    if latest_target_month != pd.Period("2025-12", freq="M"):
        raise ValueError(f"Unexpected target cutoff {latest_target_month}; expected Dec 2025 old-base data")

    labels = {h: y.shift(-h) for h in HORIZONS}
    predictions: list[dict[str, Any]] = []
    arima_failures = 0
    ridge_skips = 0
    xgb_skips = 0

    # Expanding-window, one-month-step rolling origin. Inputs stop at origin s;
    # each h-month target is the observed label at s+h.
    for origin in panel.index:
        issue_month = origin + 1
        if issue_month < BACKTEST_FIRST_ISSUE:
            continue
        usable_horizons = [
            h for h in HORIZONS
            if origin + h <= calendar_end and pd.notna(y.get(origin + h, np.nan))
        ]
        if not usable_horizons:
            continue
        history = y.loc[y.index <= origin]
        observed_history = history.dropna()
        if len(observed_history) < MIN_ARIMA_OBSERVATIONS:
            arima_fit = None
        else:
            try:
                arima_fit = fit_arima(history)
            except Exception:
                arima_fit = None
                arima_failures += 1
        max_step = max(usable_horizons)
        arima_forecasts = None
        if arima_fit is not None:
            try:
                arima_forecasts = np.asarray(arima_fit.get_forecast(steps=max_step).predicted_mean, dtype=float)
            except Exception:
                arima_failures += 1

        for horizon in usable_horizons:
            target_month = origin + horizon
            actual = float(y.loc[target_month])
            issue = origin + 1
            last_value = float(observed_history.iloc[-1]) if len(observed_history) else np.nan
            if np.isfinite(last_value):
                predictions.append({
                    "model": "Persistence", "origin_month": str(origin), "forecast_issue_month": str(issue),
                    "horizon_months": horizon, "target_month": str(target_month),
                    "actual_yoy_pct": actual, "forecast_yoy_pct": last_value,
                })
            seasonal_value = y.get(target_month - 12, np.nan)
            if pd.notna(seasonal_value):
                predictions.append({
                    "model": "SeasonalNaive", "origin_month": str(origin), "forecast_issue_month": str(issue),
                    "horizon_months": horizon, "target_month": str(target_month),
                    "actual_yoy_pct": actual, "forecast_yoy_pct": float(seasonal_value),
                })
            if arima_forecasts is not None and len(arima_forecasts) >= horizon and np.isfinite(arima_forecasts[horizon - 1]):
                predictions.append({
                    "model": "ARIMA(1,0,0)", "origin_month": str(origin), "forecast_issue_month": str(issue),
                    "horizon_months": horizon, "target_month": str(target_month),
                    "actual_yoy_pct": actual, "forecast_yoy_pct": float(arima_forecasts[horizon - 1]),
                })

            training_mask = labels[horizon].notna() & (features.index + horizon <= origin)
            x_train = features.loc[training_mask]
            y_train = labels[horizon].loc[training_mask]
            x_test = features.loc[[origin]]
            if len(y_train) >= MIN_TRAINING_SAMPLES:
                for family in ["Ridge", "XGBoost"]:
                    try:
                        estimator = fit_direct_model(family, x_train, y_train)
                        forecast = float(estimator.predict(x_test)[0])
                        predictions.append({
                            "model": family, "origin_month": str(origin), "forecast_issue_month": str(issue),
                            "horizon_months": horizon, "target_month": str(target_month),
                            "actual_yoy_pct": actual, "forecast_yoy_pct": forecast,
                        })
                    except Exception:
                        if family == "Ridge":
                            ridge_skips += 1
                        else:
                            xgb_skips += 1
            else:
                ridge_skips += 1
                xgb_skips += 1

    forecast_frame = pd.DataFrame(predictions)
    if forecast_frame.empty:
        raise RuntimeError("No backtest predictions were produced")
    forecast_frame = forecast_frame.sort_values(["horizon_months", "target_month", "model"]).reset_index(drop=True)
    forecast_frame["forecast_error_pp"] = forecast_frame["forecast_yoy_pct"] - forecast_frame["actual_yoy_pct"]
    forecast_frame["absolute_error_pp"] = forecast_frame["forecast_error_pp"].abs()
    forecast_frame.to_csv(REPORT_DIR / "rolling_origin_forecasts.csv", index=False)
    metrics = evaluate_predictions(forecast_frame)
    metrics.to_csv(REPORT_DIR / "metrics_by_model_horizon.csv", index=False, na_rep="")

    # User-configurable prototype gates; these are diagnostic, not regulatory or
    # production standards. One series is available, so coverage is 0 or 1.
    score_rows = []
    for row in metrics.to_dict(orient="records"):
        n = int(row["n_forecasts"])
        skill = row["mae_skill_vs_persistence"]
        coverage = 1.0 if n else 0.0
        if n < THRESHOLD_MIN_FORECASTS:
            decision = "INSUFFICIENT FORECASTS"
        elif not np.isfinite(skill) or skill < 0.0:
            decision = "FAIL — DOES NOT BEAT PERSISTENCE"
        else:
            decision = "PASS — BEATS PERSISTENCE"
        score_rows.append({
            "model": row["model"], "horizon_months": row["horizon_months"],
            "threshold_min_forecasts": THRESHOLD_MIN_FORECASTS, "achieved_forecasts": n,
            "threshold_min_series_coverage": 1.0, "achieved_series_coverage": coverage,
            "threshold_min_mae_skill_vs_persistence": 0.0,
            "achieved_mae_skill_vs_persistence": skill,
            "achieved_mae_pp": row["mae_pp"],
            "persistence_mae_pp": row["persistence_mae_on_paired_cases_pp"],
            "decision": decision,
            "thresholds_are_official_standards": False,
        })
    scorecard = pd.DataFrame(score_rows).sort_values(["horizon_months", "model"]).reset_index(drop=True)
    scorecard.to_csv(REPORT_DIR / "threshold_scorecard.csv", index=False, na_rep="")

    learned_families = ["ARIMA(1,0,0)", "Ridge", "XGBoost"]
    learned_rows = forecast_frame[forecast_frame["model"].isin(learned_families)].copy()
    learned_pool = learned_rows.groupby("model").agg(
        pooled_mae_pp=("absolute_error_pp", "mean"),
        pooled_rmse_pp=("forecast_error_pp", lambda s: float(np.sqrt(np.mean(np.square(s))))),
        forecast_count=("absolute_error_pp", "count"),
    ).sort_values(["pooled_mae_pp", "model"])
    best_learned_family = str(learned_pool.index[0])
    best_by_horizon = {}
    for horizon, group in metrics.groupby("horizon_months"):
        best_by_horizon[str(int(horizon))] = str(group.sort_values(["mae_pp", "model"]).iloc[0]["model"])
    selected_candidate_scorecard = scorecard[scorecard["model"] == best_learned_family]
    selected_passes_all = bool((selected_candidate_scorecard["decision"] == "PASS — BEATS PERSISTENCE").all())

    # Final direct models use all valid supervised pairs through the target cutoff.
    final_models: dict[str, dict[int, Any]] = {"Ridge": {}, "XGBoost": {}}
    final_training_rows: dict[str, dict[int, int]] = {"Ridge": {}, "XGBoost": {}}
    feature_names = list(features.columns)
    for horizon in HORIZONS:
        training_mask = labels[horizon].notna() & (features.index + horizon <= latest_target_month)
        x_train = features.loc[training_mask]
        y_train = labels[horizon].loc[training_mask]
        if len(y_train) < MIN_TRAINING_SAMPLES:
            raise RuntimeError(f"Insufficient final training rows for horizon {horizon}: {len(y_train)}")
        for family in ["Ridge", "XGBoost"]:
            estimator = fit_direct_model(family, x_train, y_train)
            final_models[family][horizon] = estimator
            final_training_rows[family][horizon] = int(len(y_train))
            artifact = {
                "model_family": family,
                "horizon_months": horizon,
                "estimator": estimator,
                "feature_columns": feature_names,
                "target_column": TARGET_COL,
                "target_source": "MoSPI 2012-base published YoY CPI series, through 2025-12",
                "training_target_cutoff": str(latest_target_month),
                "training_sample_count": int(len(y_train)),
                "fit_definition": f"feature origin s predicts target month s+{horizon}; only labels dated through the cutoff are fit",
            }
            dump_pickle(artifact, MODEL_DIR / f"{family.lower()}_h{horizon}.pkl")

    # Full-history ARIMA, plus lightweight persisted definitions for baselines.
    final_arima = fit_arima(y.loc[:latest_target_month])
    if final_arima is None:
        raise RuntimeError("Could not fit final ARIMA model")
    for horizon in HORIZONS:
        dump_pickle({
            "model_family": "ARIMA(1,0,0)", "horizon_months": horizon, "order": [1, 0, 0],
            "trend": "c", "fitted_results": final_arima, "target_column": TARGET_COL,
            "training_target_cutoff": str(latest_target_month),
            "note": "Forecast steps are selected from the stored ARIMA results at inference time.",
        }, MODEL_DIR / f"arima_100_h{horizon}.pkl")
        dump_pickle({
            "model_family": "Persistence", "horizon_months": horizon,
            "definition": "Use the latest available published target at or before the forecast origin.",
            "target_column": TARGET_COL,
        }, MODEL_DIR / f"persistence_h{horizon}.pkl")
        dump_pickle({
            "model_family": "SeasonalNaive", "horizon_months": horizon,
            "definition": "Use the observed target from the same target calendar month one year earlier (origin+h-12).",
            "target_column": TARGET_COL,
        }, MODEL_DIR / f"seasonal_naive_h{horizon}.pkl")

    # The selected model is the top learned family by pooled rolling-origin MAE.
    # It is an empirical candidate, not a claim of production readiness.
    best_artifact = {
        "selection_rule": "lowest pooled MAE among ARIMA(1,0,0), Ridge and XGBoost over all 1/3/6-month rolling-origin forecasts",
        "selected_model_family": best_learned_family,
        "selected_candidate_passes_all_prototype_gates": selected_passes_all,
        "horizons": {
            str(h): {
                "estimator": final_models[best_learned_family][h] if best_learned_family in final_models else final_arima,
                "horizon_months": h,
                "feature_columns": feature_names if best_learned_family in final_models else [],
                "training_sample_count": final_training_rows[best_learned_family][h] if best_learned_family in final_models else int(y.notna().sum()),
            }
            for h in HORIZONS
        },
        "target_column": TARGET_COL,
        "target_definition": "MoSPI-published All-India General CPI year-over-year inflation, 2012=100 base",
        "training_target_cutoff": str(latest_target_month),
        "forecast_origin_definition": "last observed month s; predict month s+h using information dated no later than s",
        "production_caveat": "2012-base series ends in December 2025 and was superseded by the 2024=100 CPI series; this is a historical prototype, not a live 2024-base model.",
    }
    best_pickle = dump_pickle(best_artifact, MODEL_DIR / "best_trained_model.pkl")
    model_by_horizon = {
        str(h): {
            "backtest_winner": best_by_horizon[str(h)],
            "learned_candidate": best_learned_family,
            "final_estimator": (final_models[best_by_horizon[str(h)]][h]
                                 if best_by_horizon[str(h)] in final_models
                                 else (final_arima if best_by_horizon[str(h)] == "ARIMA(1,0,0)" else None)),
        }
        for h in HORIZONS
    }
    best_h_pickle = dump_pickle(model_by_horizon, MODEL_DIR / "best_models_by_horizon.pkl")

    all_artifact_paths = sorted(MODEL_DIR.glob("*.pkl"))
    manifest = {
        "target": "MoSPI-published All-India General CPI YoY, 2012=100",
        "target_cutoff": str(latest_target_month),
        "backtest_issue_start": str(BACKTEST_FIRST_ISSUE),
        "horizons_months": HORIZONS,
        "selected_best_learned_family": best_learned_family,
        "selected_candidate_passes_all_prototype_gates": selected_passes_all,
        "best_model_pickle": best_pickle,
        "best_models_by_horizon_pickle": best_h_pickle,
        "artifacts": [
            {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in all_artifact_paths
        ],
    }
    (MODEL_DIR / "model_artifact_manifest.json").write_text(json.dumps(as_json_value(manifest), indent=2, allow_nan=False) + "\n", encoding="utf-8")

    config = {
        "task": "direct monthly forecast of All-India headline CPI YoY",
        "target_source": "MoSPI December 2025 CPI release Annexure VII; Dec 2025 final cross-check against February 2026 release",
        "target_cutoff": str(latest_target_month),
        "panel_calendar_end": str(calendar_end),
        "forecast_origin": "last observed month s, target is s+h; issue month is s+1",
        "backtest_issue_start": str(BACKTEST_FIRST_ISSUE),
        "horizons_months": HORIZONS,
        "rolling_origin": "monthly expanding window; no future-target labels in training",
        "minimum_training_samples": MIN_TRAINING_SAMPLES,
        "minimum_arima_observations": MIN_ARIMA_OBSERVATIONS,
        "prototype_thresholds": {
            "minimum_forecasts_per_model_horizon": THRESHOLD_MIN_FORECASTS,
            "minimum_series_coverage": 1.0,
            "minimum_mae_skill_vs_persistence": 0.0,
            "status": "internal prototype gates, not regulatory or production standards",
        },
        "features": feature_names,
        "ridge": {"alpha": 8.0, "imputer": "median + missingness indicators", "scaler": "StandardScaler"},
        "xgboost": {
            "n_estimators": 100, "max_depth": 2, "learning_rate": 0.04,
            "min_child_weight": 3, "subsample": 0.85, "colsample_bytree": 0.85,
            "reg_lambda": 8.0, "tree_method": "hist", "random_state": 2026,
        },
        "arima": {"order": [1, 0, 0], "trend": "c", "missing_values": "statsmodels state-space handling"},
        "versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__,
                     "scikit_learn": sklearn.__version__, "statsmodels": statsmodels.__version__, "xgboost": xgboost.__version__},
        "fit_counts": final_training_rows,
        "fit_skips": {"arima_failures": arima_failures, "ridge_skips": ridge_skips, "xgboost_skips": xgb_skips},
    }
    (REPORT_DIR / "training_config.json").write_text(json.dumps(as_json_value(config), indent=2, allow_nan=False) + "\n", encoding="utf-8")

    metrics_lookup = metrics.set_index(["model", "horizon_months"])
    pass_lines = []
    for _, row in scorecard.iterrows():
        pass_lines.append(
            f"| {row['model']} | {int(row['horizon_months'])} | {int(row['achieved_forecasts'])} / {THRESHOLD_MIN_FORECASTS} | "
            f"{row['achieved_mae_pp']:.3f} | {row['persistence_mae_pp']:.3f} | "
            f"{row['achieved_mae_skill_vs_persistence']:.3f} / 0.000 | {row['decision']} |"
        )
    learned_maes = learned_pool.reset_index().to_dict(orient="records")
    best_summary = learned_pool.loc[best_learned_family]
    best_candidate_gate_text = "cleared all three per-horizon gates" if selected_passes_all else "did not clear all three per-horizon gates"
    best_overall_rows = [
        f"| {h} | {model} | {metrics_lookup.loc[(model, h), 'mae_pp']:.3f} |"
        for h, model in sorted(((int(k), v) for k, v in best_by_horizon.items()))
    ]
    evaluation = f"""# India CPI model evaluation

## Scope and method

- **Target:** MoSPI-published All-India General CPI YoY inflation rate, 2012=100; 142 observed target months, through December 2025.
- **Forecast origin:** last observed month `s`; horizon `h` predicts the published target for `s+h`; information dated after `s` is excluded.
- **Backtest:** monthly expanding-window rolling origins; issue months begin January 2018; horizons are 1, 3 and 6 months.
- **Models:** persistence, seasonal naive, ARIMA(1,0,0), Ridge and XGBoost. Direct regressors are refit at every origin/horizon. Missing predictors are imputed only inside each training fold; CPI targets are never imputed.
- **Thresholds:** at least {THRESHOLD_MIN_FORECASTS} forecasts and MAE skill versus persistence ≥ 0. These are prototype gates, not formal standards.

## Threshold values versus measured outcomes

| Model | Horizon (months) | Forecasts (minimum 60) | MAE (pp) | Persistence MAE (pp) | Skill (minimum 0) | Decision |
|---|---:|---:|---:|---:|---:|---|
{chr(10).join(pass_lines)}

## Best candidates

The lowest pooled MAE among the three learned model families was **{best_learned_family}** (pooled MAE {float(best_summary['pooled_mae_pp']):.3f} pp over {int(best_summary['forecast_count'])} forecasts). It {best_candidate_gate_text}; see the threshold table before using it. The best backtested model by horizon, including simple baselines, was:

| Horizon (months) | Lowest-MAE model | MAE (pp) |
|---:|---|---:|
{chr(10).join(best_overall_rows)}

## Interpretation and limits

This is a transparent prototype evaluation, not a “perfect” or production-certified model. The target ends at December 2025 because MoSPI replaced the 2012=100 series with a 2024=100 series in February 2026. The archived Kaggle/data.gov.in category features end in August 2025, and historical release timestamps are unavailable; feature publication-lag leakage cannot be ruled out. Vintage differences between the archived CPI table and MoSPI’s final published inflation series are documented in `normalization_report.md` and `source_research_notes.md`. Retrain and revalidate on the 2024-base series before deployment.

Final fitted candidates are saved as horizon-specific `.pkl` files; `models/best_trained_model.pkl` contains the best learned family selected by pooled rolling-origin MAE. The artifact is historical and must not be applied directly to the new CPI base.
"""
    (REPORT_DIR / "evaluation_summary.md").write_text(evaluation, encoding="utf-8")

    selection = {
        "selected_best_learned_family": best_learned_family,
        "selected_learned_family_pooled_metrics": learned_pool.loc[best_learned_family].to_dict(),
        "selected_candidate_passes_all_prototype_gates": selected_passes_all,
        "best_backtested_model_by_horizon": best_by_horizon,
        "pooled_learned_family_metrics": learned_maes,
        "series_end": str(latest_target_month),
        "warning": "The 2012-base CPI series has been superseded; the learned candidate is not live-production certified.",
    }
    (REPORT_DIR / "model_selection.json").write_text(json.dumps(as_json_value(selection), indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "forecast_rows": int(len(forecast_frame)),
        "metrics": metrics[["model", "horizon_months", "n_forecasts", "mae_pp", "rmse_pp", "mae_skill_vs_persistence"]].to_dict(orient="records"),
        "selected_best_learned_family": best_learned_family,
        "selected_candidate_passes_all_prototype_gates": selected_passes_all,
        "best_backtested_model_by_horizon": best_by_horizon,
        "final_training_rows": final_training_rows,
        "fit_skips": {"arima_failures": arima_failures, "ridge_skips": ridge_skips, "xgboost_skips": xgb_skips},
        "model_dir": str(MODEL_DIR),
        "report_dir": str(REPORT_DIR),
    }, indent=2, default=as_json_value))


if __name__ == "__main__":
    main()
