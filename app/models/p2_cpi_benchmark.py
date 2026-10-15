"""Optional one-month CPI benchmarks trained from the P2 public research panel.

These frozen external benchmarks are isolated from the application's MoSPI
2024-base model package because their target and training inputs are different.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "app" / "models" / "p2_cpi_benchmark_assets"
DATA_FILE = PACKAGE / "source" / "master_data1.csv"
ARTIFACTS = PACKAGE / "artifacts"
EXPECTED_COMMIT = "ce8abb01d2ec0fd7524638995281e32a8142f1d1"
EXPECTED_DATASET_SHA256 = "5ce2206c99358cc5816de7372fb6d1fe1952348834f5c4f273d03ed55135ae7f"
TARGET = "cpi_inflation"
MACRO_COLUMNS = (
    "iip",
    "m3",
    "repo_rate",
    "tbill_91d",
    "gsec_10yr",
    "inr_usd",
    "fed_funds_rate",
    "crude_oil_brent",
    "term_spread",
)
MODEL_FILES = {
    "p2_arima": "arima_300.joblib",
    "p2_arimax": "arimax_300_converged.joblib",
    "p2_elasticnet": "elasticnet.joblib",
    "p2_xgboost": "xgboost_native.json",
}
MODEL_IDS = ("p2_persistence", *MODEL_FILES)
REQUIRED_ARTIFACTS = (
    "arima_300.joblib",
    "arimax_300.joblib",
    "elasticnet.joblib",
    "xgboost.joblib",
    "walk_forward_metrics.csv",
    "walk_forward_predictions.csv",
    "training_metadata.json",
    "LICENSE-p2-india-cpi-forecasting.txt",
)
ARIMAX_SCALER_FILE = "arimax_scaler.json"
RETRAINED_MANIFEST_FILE = "retrained_models_manifest.json"


class P2ModelNotReadyError(RuntimeError):
    """An external P2 artifact is absent or unsuitable for inference."""


def _dataset_hash() -> str:
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"P2 benchmark dataset is missing: {DATA_FILE}")
    digest = hashlib.sha256(DATA_FILE.read_bytes()).hexdigest()
    if digest != EXPECTED_DATASET_SHA256:
        raise ValueError("P2 benchmark dataset checksum does not match its pinned source.")
    return digest


def _load_raw() -> pd.DataFrame:
    _dataset_hash()
    raw = pd.read_csv(DATA_FILE)
    required = {"date", TARGET, *MACRO_COLUMNS}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"P2 benchmark dataset is missing columns: {missing}")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise")
    raw = raw.sort_values("date").set_index("date")
    if raw.index.has_duplicates:
        raise ValueError("P2 benchmark dataset contains duplicate dates.")
    expected = pd.date_range(raw.index.min(), raw.index.max(), freq="MS")
    if not raw.index.equals(expected):
        raise ValueError("P2 benchmark dataset is not a complete month-start series.")
    for column in (TARGET, *MACRO_COLUMNS):
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    if raw[[TARGET, *MACRO_COLUMNS]].isna().any().any():
        raise ValueError("P2 benchmark dataset contains missing or non-numeric model inputs.")
    return raw


def _features(raw: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(index=raw.index)
    for column in MACRO_COLUMNS:
        frame[f"{column}_lag1"] = raw[column].shift(1)
    for lag in (1, 2, 3):
        frame[f"cpi_lag{lag}"] = raw[TARGET].shift(lag)
    frame["m3_lag12"] = raw["m3"].shift(12)
    return frame


@lru_cache(maxsize=1)
def _training_panel() -> pd.DataFrame:
    raw = _load_raw()
    panel = _features(raw)
    panel[TARGET] = raw[TARGET]
    panel = panel.dropna()
    if panel.empty:
        raise ValueError("P2 benchmark dataset has insufficient history after lag construction.")
    return panel


def _future_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Build the next month's lagged predictors using only the available panel."""
    next_month = raw.index[-1] + pd.offsets.MonthBegin(1)
    row: dict[str, float] = {}
    for column in MACRO_COLUMNS:
        row[f"{column}_lag1"] = float(raw[column].iloc[-1])
    for lag in (1, 2, 3):
        row[f"cpi_lag{lag}"] = float(raw[TARGET].iloc[-lag])
    row["m3_lag12"] = float(raw["m3"].iloc[-12])
    return pd.DataFrame([row], index=pd.DatetimeIndex([next_month]))


def _metadata() -> dict[str, Any]:
    path = ARTIFACTS / "training_metadata.json"
    if not path.is_file():
        raise P2ModelNotReadyError(
            "P2 model artifacts have not been imported. Download the training ZIP "
            "from Drive and run scripts/import_p2_cpi_bundle.py."
        )
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("P2 model metadata must be a JSON object.")
    if metadata.get("source_commit") != EXPECTED_COMMIT:
        raise ValueError("P2 model artifacts were trained from an unexpected repository commit.")
    if metadata.get("dataset_sha256") != _dataset_hash():
        raise ValueError("P2 model artifacts do not match the installed P2 training dataset.")
    return metadata


def _retrained_manifest() -> dict[str, Any]:
    path = ARTIFACTS / RETRAINED_MANIFEST_FILE
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("P2 retrained model manifest must be a JSON object.")
    if (
        manifest.get("source_commit") != EXPECTED_COMMIT
        or manifest.get("dataset_sha256") != _dataset_hash()
    ):
        raise ValueError("P2 retrained model manifest does not match the pinned source data.")
    return manifest


def p2_model_registry() -> dict[str, Any]:
    """List P2 model availability and the notebook's time-ordered metrics."""
    dataset_hash = _dataset_hash()
    metadata_path = ARTIFACTS / "training_metadata.json"
    installed = metadata_path.is_file()
    metrics_path = ARTIFACTS / "walk_forward_metrics.csv"
    metrics: list[dict[str, Any]] = []
    if installed:
        metadata = _metadata()
        missing = [name for name in REQUIRED_ARTIFACTS if not (ARTIFACTS / name).is_file()]
        if missing:
            raise FileNotFoundError(f"P2 model package is incomplete: {missing}")
        retrained = _retrained_manifest()
        with metrics_path.open(encoding="utf-8-sig", newline="") as stream:
            metrics = [
                {
                    **row,
                    "mae_percentage_points": float(row["mae_percentage_points"]),
                    "rmse_percentage_points": float(row["rmse_percentage_points"]),
                    "test_observations": int(row["n_test"]),
                }
                for row in csv.DictReader(stream)
            ]
        if retrained:
            for refreshed_metric in retrained.get("metrics", []):
                metrics = [
                    refreshed_metric if item["model"] == refreshed_metric["model"] else item
                    for item in metrics
                ]
    else:
        metadata = {}
        retrained = {}
    model_status = {"p2_persistence": "available"}
    for model_id, filename in MODEL_FILES.items():
        model_status[model_id] = (
            "not_imported" if not installed
            else "available" if (ARTIFACTS / filename).is_file()
            else "requires_retraining" if model_id == "p2_arimax"
            else "requires_native_conversion" if model_id == "p2_xgboost"
            else "missing"
        )
    if installed and (
        not retrained.get("arimax", {}).get("final_fit_converged", False)
        or not retrained.get("arimax", {}).get("converged_at_all_walk_forward_origins", False)
        or not (ARTIFACTS / ARIMAX_SCALER_FILE).is_file()
    ):
        model_status["p2_arimax"] = "requires_convergence_review"
    if installed and (
        model_status["p2_arimax"] == "available"
        and not retrained.get("arimax", {}).get("converged_at_all_walk_forward_origins", False)
    ):
        model_status["p2_arimax"] = "requires_convergence_review"
    if installed and (ARTIFACTS / MODEL_FILES["p2_xgboost"]).is_file() and not retrained:
        model_status["p2_xgboost"] = "requires_native_conversion"
    raw = _load_raw()
    panel = _training_panel()
    warning_messages = [
        "Separate source dataset/target; do not combine its CPI levels or metrics with the app's MoSPI 2024-base package.",
        "Experimental one-step benchmark. Historical source release vintages were not verified.",
        "The validation period is a historical comparison, not a prospective production test.",
    ]
    if model_status["p2_arimax"] != "available":
        warning_messages.append(
            "ARIMAX is not served until its retrained final fit and all walk-forward fits pass convergence checks."
        )
    else:
        warning_messages.append(
            "ARIMAX was retrained with standardized, non-redundant inputs; convergence was verified for every walk-forward origin."
        )
    if model_status["p2_xgboost"] == "available":
        warning_messages.append("XGBoost uses its native JSON model format rather than version-sensitive pickle serialization.")
    else:
        warning_messages.append("XGBoost requires a native JSON artifact; the legacy joblib file is not loaded.")
    return {
        "status": "available" if installed else "dataset_available_models_not_imported",
        "mode": "external_research_benchmark",
        "source_repository": "https://github.com/ketandeshmukh1920/p2-india-cpi-forecasting",
        "source_commit": EXPECTED_COMMIT,
        "source_license": "MIT; see app/models/p2_cpi_benchmark_assets/source/LICENSE",
        "dataset_sha256": dataset_hash,
        "dataset_start": raw.index.min().strftime("%Y-%m"),
        "dataset_end": raw.index.max().strftime("%Y-%m"),
        "target": "Repository CPI inflation (percent; not the app's MoSPI 2024-base target)",
        "training_observations": int(len(panel)),
        "supported_horizons_months": [1],
        "models": model_status,
        "metrics": metrics,
        "training_versions": retrained.get("versions", metadata.get("versions", {})),
        "retrained_model_manifest": retrained,
        "warnings": warning_messages,
    }


@lru_cache(maxsize=4)
def _load_model(model_id: str) -> Any:
    if model_id not in MODEL_FILES:
        raise ValueError(f"model must be one of: {', '.join(MODEL_FILES)}")
    _metadata()
    missing = [name for name in REQUIRED_ARTIFACTS if not (ARTIFACTS / name).is_file()]
    if missing:
        raise FileNotFoundError(f"P2 model package is incomplete: {missing}")
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("P2 model loading requires joblib; install the econometrics extra.") from exc
    if model_id == "p2_arimax":
        manifest = _retrained_manifest()
        arimax_status = p2_model_registry()["models"]["p2_arimax"]
        if arimax_status != "available":
            raise P2ModelNotReadyError(
                "The P2 ARIMAX model is disabled until its final fit and every "
                "walk-forward fit converge; run scripts/retrain_p2_compat_models.py."
            )
        model = joblib.load(ARTIFACTS / MODEL_FILES[model_id])
        scaler = json.loads((ARTIFACTS / ARIMAX_SCALER_FILE).read_text(encoding="utf-8"))
        if not model.mle_retvals.get("converged", False):
            raise P2ModelNotReadyError("The imported P2 ARIMAX artifact did not converge.")
        if manifest.get("arimax", {}).get("feature_columns") != scaler.get("feature_columns"):
            raise ValueError("ARIMAX scaler features do not match the retrained model manifest.")
        return {"model": model, "scaler": scaler}
    if model_id == "p2_xgboost":
        try:
            import xgboost
        except ImportError as exc:
            raise RuntimeError("P2 XGBoost loading requires xgboost; install the econometrics extra.") from exc
        model_path = ARTIFACTS / MODEL_FILES[model_id]
        if not model_path.is_file():
            raise P2ModelNotReadyError(
                "P2 XGBoost's native JSON artifact is absent; run "
                "scripts/retrain_p2_compat_models.py. Legacy pickle files are not loaded."
            )
        model = xgboost.Booster()
        model.load_model(model_path)
        return model
    return joblib.load(ARTIFACTS / MODEL_FILES[model_id])


def p2_forecast(model_id: str, horizon: int = 1) -> dict[str, Any]:
    """Forecast one month ahead from the frozen P2 panel using an imported artifact."""
    if horizon != 1:
        raise ValueError("P2 benchmark artifacts support one-month-ahead forecasts only.")
    if model_id not in MODEL_IDS:
        raise ValueError(f"model must be one of: {', '.join(MODEL_IDS)}")
    raw = _load_raw()
    next_features = _future_features(raw)
    if model_id == "p2_persistence":
        prediction = float(raw[TARGET].iloc[-1])
    else:
        panel = _training_panel()
        model = _load_model(model_id)
        if model_id == "p2_arima":
            prediction = float(model.forecast(steps=1).iloc[0])
        elif model_id == "p2_arimax":
            scaler = model["scaler"]
            columns = scaler["feature_columns"]
            features = next_features.reindex(columns=columns).to_numpy()
            scaled = (features - scaler["mean"]) / scaler["scale"]
            prediction = float(model["model"].forecast(steps=1, exog=scaled).iloc[0])
        elif model_id == "p2_xgboost":
            import xgboost

            columns = list(panel.columns.drop(TARGET))
            features = next_features.reindex(columns=columns)
            matrix = xgboost.DMatrix(features, feature_names=columns)
            prediction = float(model.predict(matrix)[0])
        else:
            prediction = float(model.predict(next_features.reindex(columns=panel.columns.drop(TARGET)))[0])
    if not math.isfinite(prediction):
        raise ValueError(f"{model_id} returned a non-finite forecast.")
    origin = raw.index[-1]
    target = next_features.index[0]
    return {
        "series_id": "cpi_yoy",
        "model": model_id,
        "variant": "p2_macro_panel",
        "status": "computed",
        "mode": "external_research_benchmark",
        "origin": origin.strftime("%Y-%m"),
        "target_month": target.strftime("%Y-%m"),
        "horizon_months": 1,
        "forecasts": [{"step": 1, "value": prediction}],
        "source_observations": int(len(raw)),
        "source": "p2_repository_macro_panel",
        "unit": "percent",
        "dataset_start": raw.index.min().strftime("%Y-%m"),
        "dataset_end": origin.strftime("%Y-%m"),
        "source_commit": EXPECTED_COMMIT,
        "warnings": [
            "External research benchmark, based on the P2 repository's frozen panel; not the live app data.",
            "The P2 target definition and vintage differ from the app's MoSPI 2024-base target.",
            "Experimental forecast only; not policy advice or a validated production forecast.",
        ],
    }
