"""Inference adapters for the locally packaged India CPI research models.

The feature panel and artifacts are a frozen research snapshot. They are not
silently mixed with uploaded series because the package's training feature
definitions require matching release vintages and lag rules.
"""
from __future__ import annotations

import json
import math
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "app" / "models" / "india_macro_models_enriched"
PANEL = PACKAGE / "data" / "processed" / "enriched_training_panel.csv"
VARIANTS = ("base", "wpi_old", "wpi_current", "credit", "wpi_old_credit", "wpi_current_credit", "all")
HORIZONS = (1, 3, 6)
METRICS = PACKAGE / "results" / "rolling_origin_metrics.csv"
MODEL_NAMES = {
    "ARIMA_1_0_0": "arima",
    "Ridge": "ridge",
    "XGBoost": "xgboost",
    "seasonal_naive": "seasonal_naive",
    "persistence": "persistence",
}


def packaged_model_registry() -> dict[str, Any]:
    """Expose packaged model inventory and its recorded rolling holdout metrics."""
    if not METRICS.is_file():
        raise FileNotFoundError("The enriched model evaluation metrics are missing.")
    rows: list[dict[str, Any]] = []
    with METRICS.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            rows.append({
                "model": MODEL_NAMES.get(row["model"], row["model"].lower()),
                "model_label": row["model"], "variant": row["variant"],
                "horizon_months": int(row["horizon_months"]),
                "test_origins": int(row["n_test"]),
                "mae_pp": float(row["mae_pp"]), "rmse_pp": float(row["rmse_pp"]),
                "bias_pp": float(row["bias_pp"]),
                "test_start": row["test_start"], "test_end": row["test_end"],
            })
    manifest_path = PACKAGE / "model_card_and_training_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    return {
        "status": "available", "mode": "packaged_research_artifacts",
        "target": "India CPI year-over-year inflation", "unit": "percent",
        "variants": list(VARIANTS), "supported_horizons_months": list(HORIZONS),
        "test_period": manifest.get("test_period"), "metrics": rows,
        "warnings": manifest.get("important_limitations", [
            "Experimental research artifacts; holdout performance does not establish deployment readiness.",
        ]),
    }


def _panel() -> pd.DataFrame:
    if not PANEL.is_file():
        raise FileNotFoundError("The enriched model training panel is missing.")
    frame = pd.read_csv(PANEL)
    if "period" not in frame or "observed_cpi_yoy_pct" not in frame:
        raise ValueError("The enriched model panel has an unexpected schema.")
    frame["period"] = pd.PeriodIndex(frame["period"].astype(str), freq="M")
    frame = frame.sort_values("period")
    frame = frame.loc[frame["observed_cpi_yoy_pct"].notna()]
    if frame.empty:
        raise ValueError("The enriched model panel has no observed CPI target rows.")
    return frame


def _ridge_predict(variant: str, horizon: int, row: pd.Series, target_period: pd.Period) -> float:
    artifact_path = PACKAGE / "models" / variant / f"ridge_cpi_yoy_h{horizon}.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    columns = artifact["feature_order"]
    values = {name: row.get(name, np.nan) for name in columns}
    angle = 2 * math.pi * (target_period.month - 1) / 12
    values["target_month_sin"] = math.sin(angle)
    values["target_month_cos"] = math.cos(angle)
    vector = pd.Series(values).reindex(columns).apply(pd.to_numeric, errors="coerce")
    medians = pd.Series(artifact["median"]).reindex(columns)
    vector = vector.fillna(medians).fillna(0.0).to_numpy(dtype=float)
    mean = np.array([artifact["mean"][name] for name in columns], dtype=float)
    scale = np.array([artifact["scale"][name] for name in columns], dtype=float)
    coef = np.array([artifact["coefficients"][name] for name in columns], dtype=float)
    prediction = float(((vector - mean) / scale) @ coef + float(artifact["target_intercept"]))
    if not math.isfinite(prediction):
        raise ValueError("Ridge returned a non-finite forecast.")
    return prediction


def _xgboost_predict(variant: str, horizon: int, row: pd.Series, target_period: pd.Period) -> float:
    try:
        import xgboost as xgb
    except ImportError as exc:
        raise RuntimeError("XGBoost is optional; install the project's econometrics extra to use it.") from exc
    artifact_path = PACKAGE / "models" / variant / f"ridge_cpi_yoy_h{horizon}.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    columns = artifact["feature_order"]
    values = {name: row.get(name, np.nan) for name in columns}
    angle = 2 * math.pi * (target_period.month - 1) / 12
    values["target_month_sin"] = math.sin(angle)
    values["target_month_cos"] = math.cos(angle)
    frame = pd.DataFrame([[pd.to_numeric(values.get(name), errors="coerce") for name in columns]], columns=columns)
    booster = xgb.Booster()
    booster.load_model(str(PACKAGE / "models" / variant / f"xgboost_cpi_yoy_h{horizon}.json"))
    result = float(booster.predict(xgb.DMatrix(frame, feature_names=columns, missing=np.nan))[0])
    if not math.isfinite(result):
        raise ValueError("XGBoost returned a non-finite forecast.")
    return result


def _arima_predict(frame: pd.DataFrame, horizon: int) -> float:
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError as exc:
        raise RuntimeError("ARIMA requires the project's econometrics dependencies.") from exc
    values = frame["observed_cpi_yoy_pct"].astype(float).to_numpy()
    model = ARIMA(values, order=(1, 0, 0), trend="c").fit()
    return float(model.forecast(steps=horizon)[-1])


def enriched_forecast(model: str, variant: str, horizon: int) -> dict[str, Any]:
    """Return one direct horizon forecast from the frozen packaged feature panel."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of: {', '.join(VARIANTS)}")
    if model not in {"ridge", "xgboost", "arima", "ensemble"}:
        raise ValueError("model must be seasonal_naive, ridge, xgboost, arima, or ensemble")
    if horizon not in HORIZONS:
        raise ValueError("Packaged models support direct horizons of 1, 3, or 6 months")
    frame = _panel()
    latest = frame.iloc[-1]
    origin = latest["period"]
    target = origin + horizon
    parts: dict[str, float] = {}
    if model in ("ridge", "ensemble"):
        parts["ridge"] = _ridge_predict(variant, horizon, latest, target)
    if model in ("xgboost", "ensemble"):
        parts["xgboost"] = _xgboost_predict(variant, horizon, latest, target)
    if model == "arima":
        parts["arima"] = _arima_predict(frame, horizon)
    if model == "ensemble":
        prediction = float(np.mean(list(parts.values())))
    else:
        prediction = next(iter(parts.values()))
    effective_variant = "univariate" if model == "arima" else variant
    manifest_path = PACKAGE / "model_card_and_training_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    return {
        "series_id": "cpi_yoy", "model": model, "variant": effective_variant,
        "status": "computed", "mode": "frozen_research_model",
        "origin": str(origin), "target_month": str(target), "horizon_months": horizon,
        "forecasts": [{"step": horizon, "value": prediction}],
        "component_forecasts": parts,
        "source_observations": int(frame["observed_cpi_yoy_pct"].notna().sum()),
        "source": "packaged_observed_macro_panel", "unit": "percent",
        "dataset_start": str(frame["period"].iloc[0]), "dataset_end": str(origin),
        "training_test_period": manifest.get("test_period"),
        "warnings": [
            "Forecast uses the frozen feature panel bundled with the model package; newly uploaded project observations are not yet used to rebuild these lagged predictors.",
            "Experimental research model only. The package's 24-month holdout is small and does not establish deployment performance or causal policy effects.",
            *(["Ensemble is an unweighted Ridge/XGBoost average and has not been separately validated."] if model == "ensemble" else []),
        ],
    }
