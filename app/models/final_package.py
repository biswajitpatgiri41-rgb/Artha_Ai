"""Read-only access to the final CPI package's versioned artifacts.

The package's fitted estimators are serialized joblib files. They are deliberately
not deserialized by the API: the runtime serves the checksum-verified forecast,
evaluation, and target-data files exported by the reproducible training workflow.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


_MODEL_DIR = Path(__file__).resolve().parent
_TRACKED_PACKAGE_ROOT = _MODEL_DIR / "Final_data_and_models" / "Final_model_sets" / "India_CPI_Model_Package"


def _select_default_package_root() -> Path:
    """Choose an accessible package root, preferring the tracked deployment copy."""
    candidates = [
        _MODEL_DIR / "runtime_final_cpi_package",
        _TRACKED_PACKAGE_ROOT,
    ]
    for candidate in candidates:
        try:
            if (candidate / "SHA256SUMS.txt").is_file():
                with (candidate / "SHA256SUMS.txt").open(encoding="utf-8"):
                    return candidate
        except OSError:
            continue
    return _TRACKED_PACKAGE_ROOT


DEFAULT_PACKAGE_ROOT = _select_default_package_root()
PACKAGE_ROOT = Path(os.environ.get("FINAL_MODEL_PACKAGE_DIR", DEFAULT_PACKAGE_ROOT)).expanduser().resolve()
ARTIFACTS_ROOT = PACKAGE_ROOT / "artifacts"

VARIANTS = {
    "mospi_2024_base": "mospi_2024_base",
    "mospi_2024_base_extended": "mospi_2024_base_extended",
    "oecd_long_history_sensitivity": "oecd_long_history_sensitivity",
}
MODEL_LABELS = {
    "seasonal_naive": "SeasonalNaive",
    "ets": "ETS",
    "arima": "ARIMA",
    "sarima": "SARIMA",
    "sarimax": "SARIMAX",
    "var": "VAR",
    "xgboost": "XGBoost",
    "ensemble": "Ensemble",
}


class ModelPackageIntegrityError(RuntimeError):
    """A required artifact is present but is not covered by package integrity data."""


@lru_cache(maxsize=1)
def _checksums() -> dict[str, str]:
    manifest = PACKAGE_ROOT / "SHA256SUMS.txt"
    if not manifest.is_file():
        raise FileNotFoundError("The final CPI package checksum manifest is missing.")
    checksums: dict[str, str] = {}
    with manifest.open(encoding="utf-8-sig") as stream:
        for line in stream:
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                checksums[parts[1].lstrip("* ").replace("\\", "/")] = parts[0].lower()
    return checksums


def _verified_path(relative_path: str) -> Path:
    """Resolve a fixed package-relative path and verify its recorded SHA-256."""
    normalized = relative_path.replace("\\", "/").lstrip("/")
    path = (PACKAGE_ROOT / normalized).resolve()
    if not path.is_relative_to(PACKAGE_ROOT):
        raise ModelPackageIntegrityError("Package artifact path is outside the configured package root.")
    if not path.is_file():
        raise FileNotFoundError(f"Required final model artifact is missing: {normalized}")
    expected = _checksums().get(normalized)
    if not expected:
        raise ModelPackageIntegrityError(f"No package checksum is recorded for {normalized}.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise ModelPackageIntegrityError(f"Final model artifact checksum mismatch: {normalized}")
    return path


def _read_json(relative_path: str) -> dict[str, Any]:
    payload = json.loads(_verified_path(relative_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {relative_path}.")
    return payload


def _read_csv(relative_path: str) -> list[dict[str, str]]:
    with _verified_path(relative_path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _variant_dir(variant: str) -> str:
    try:
        return VARIANTS[variant]
    except KeyError as exc:
        raise ValueError(f"variant must be one of: {', '.join(VARIANTS)}") from exc


def _float(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def load_packaged_cpi_target() -> list[dict[str, Any]]:
    """Read the bundled MoSPI 2024-base target without importing model code."""
    rows = _read_csv("artifacts/mospi_2024_base_target.csv")
    observations: dict[str, dict[str, Any]] = {}
    for row in rows:
        period = str(row.get("date", "")).strip()
        value = _float(row.get("target_yoy"))
        if len(period) != 7 or period[4] != "-" or value is None:
            continue
        observations[period] = {
            "date": f"{period}-01",
            "value": value,
            "source": "MoSPI 2024-base final CPI model dataset",
            "target_origin": row.get("target_origin") or None,
            "base_year": "2024",
        }
    if not observations:
        raise ValueError("The bundled MoSPI target contains no valid monthly observations.")
    return [observations[key] for key in sorted(observations)]


def final_model_registry() -> dict[str, Any]:
    """Expose recorded model metrics and weights for every packaged CPI variant."""
    metrics: list[dict[str, Any]] = []
    all_models: set[str] = set()
    supported_horizons: set[int] = set()
    for variant in VARIANTS:
        folder = f"artifacts/{variant}"
        metadata = _read_json(f"{folder}/metadata.json")
        weight_rows = _read_csv(f"{folder}/ensemble_weights.csv")
        weights = {
            (int(row["horizon_months"]), row["model"]): _float(row.get("weight"))
            for row in weight_rows
            if row.get("horizon_months", "").isdigit()
        }
        for row in _read_csv(f"{folder}/test_metrics.csv"):
            horizon = int(row["horizon_months"])
            label = row["model"]
            model_id = "seasonal_naive" if label == "SeasonalNaive" else label.lower()
            supported_horizons.add(horizon)
            all_models.add(model_id)
            metrics.append({
                "model": model_id,
                "model_label": label,
                "variant": variant,
                "horizon_months": horizon,
                "test_origins": int(row["n_test"]),
                "mae_pp": _float(row.get("MAE_pp")),
                "rmse_pp": _float(row.get("RMSE_pp")),
                "bias_pp": _float(row.get("bias_pp")),
                "test_start": None,
                "test_end": None,
                "coverage_80": _float(row.get("test_coverage80_using_dev_calibration")),
                "coverage_95": _float(row.get("test_coverage95_using_dev_calibration")),
                "model_weight": weights.get((horizon, label)),
                "package_created_at": metadata.get("created_utc"),
            })
    return {
        "status": "available",
        "mode": "checksum_verified_final_package_artifacts",
        "target": "India CPI Combined General Group YoY inflation",
        "unit": "percent",
        "variants": list(VARIANTS),
        "models": sorted(all_models),
        "supported_horizons_months": sorted(supported_horizons),
        "test_period": None,
        "metrics": metrics,
        "warnings": [
            "These metrics are from the package's comparison period; it was used to compare feature specifications and is not an untouched final holdout.",
            "The package target ends at 2026-08 and has no historical real-time release vintages.",
            "Saved model forecasts are research snapshots, not live predictions from newly retrieved data.",
            "Serialized joblib estimators are not loaded by the API; runtime responses use checksum-verified CSV and JSON exports.",
        ],
    }


def final_model_registry_records() -> list[dict[str, Any]]:
    """Build candidate registry records from verified model artifacts and metrics."""
    records: list[dict[str, Any]] = []
    for variant in VARIANTS:
        folder = f"artifacts/{variant}"
        package_metadata = _read_json(f"{folder}/metadata.json")
        model_metadata = _read_json(f"{folder}/models/model_metadata.json")
        metrics_rows = _read_csv(f"{folder}/test_metrics.csv")
        model_names = sorted({row["model"] for row in metrics_rows if row.get("model")})
        gains = _read_csv(f"{folder}/diagnostics/xgboost_gain_importance.csv")
        for model_name in model_names:
            if model_name == "XGBoost":
                model_files = [
                    f"{folder}/models/XGBoost_direct_h{h}.joblib"
                    for h in model_metadata.get("horizons", [1, 3, 6, 12])
                ]
            elif model_name == "Ensemble":
                model_files = [f"{folder}/models/model_registry.joblib", f"{folder}/ensemble_weights.csv"]
            else:
                model_files = [f"{folder}/models/{model_name}.joblib"]
            resolved = [_verified_path(path) for path in model_files]
            bundle_hash = hashlib.sha256()
            for relative, path in zip(model_files, resolved):
                bundle_hash.update(relative.encode("utf-8"))
                bundle_hash.update(b"\0")
                bundle_hash.update(hashlib.sha256(path.read_bytes()).digest())

            rows = [row for row in metrics_rows if row.get("model") == model_name]
            backtest_metrics: dict[str, float] = {}
            horizons = sorted({int(row["horizon_months"]) for row in rows})
            for row in rows:
                horizon = int(row["horizon_months"])
                for source, suffix in (("MAE_pp", "mae_pp"), ("RMSE_pp", "rmse_pp"), ("bias_pp", "bias_pp")):
                    value = _float(row.get(source))
                    if value is not None:
                        backtest_metrics[f"h{horizon}_{suffix}"] = value

            if model_name == "SARIMAX":
                features = model_metadata.get("exogenous_columns", [])
            elif model_name == "VAR":
                features = model_metadata.get("var_columns", [])
            elif model_name == "XGBoost":
                features = sorted({row["feature"] for row in gains if row.get("feature")})
            elif model_name == "Ensemble":
                features = list(model_metadata.get("component_fit", []))
            else:
                features = []

            cutoff = str(model_metadata.get("target_end", ""))
            created = str(package_metadata.get("created_utc", ""))
            target = (
                "OECD India monthly CPI YoY sensitivity target (%)"
                if variant == "oecd_long_history_sensitivity"
                else "MoSPI India CPI 2024-base Combined General Group YoY (%)"
            )
            records.append({
                "model_name": model_name,
                "version": f"{variant}@{model_metadata.get('forecast_origin', cutoff)}",
                "target": target,
                "forecast_horizons": horizons,
                "training_cutoff": f"{cutoff}-01",
                "data_vintage": str(model_metadata.get("target_end", cutoff)),
                "feature_list": features,
                "hyperparameters": {},
                "backtest_metrics": backtest_metrics,
                "artifact_hash": bundle_hash.hexdigest(),
                "library_versions": {
                    **{key: str(value) for key, value in package_metadata.get("versions", {}).items()},
                    "python": str(package_metadata.get("python", "not recorded")),
                },
                "git_commit": None,
                "status": "CANDIDATE",
                "created_at": created,
            })
    return records


def final_regime_probabilities(variant: str = "mospi_2024_base_extended") -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Read checksum-verified exploratory HMM probabilities and their caveats."""
    variant_dir = _variant_dir(variant)
    base = f"artifacts/{variant_dir}/diagnostics"
    rows = _read_csv(f"{base}/regime_probabilities.csv")
    metadata = _read_json(f"{base}/regime_model_metadata.json")
    return rows, metadata


def final_model_forecast(model: str, variant: str, horizon: int) -> dict[str, Any]:
    """Return a previously scored forecast row for a registered model and horizon."""
    variant_dir = _variant_dir(variant)
    if not 1 <= horizon <= 12:
        raise ValueError("horizon must be between 1 and 12 months")
    if model not in MODEL_LABELS:
        raise ValueError(f"model must be one of: {', '.join(MODEL_LABELS)}")
    folder = f"artifacts/{variant_dir}"
    forecasts = _read_csv(f"{folder}/forecasts.csv")
    matches = [row for row in forecasts if row.get("horizon_months", "").isdigit()
               and int(row["horizon_months"]) == horizon]
    if not matches:
        raise LookupError(f"No stored {variant} forecast is available at horizon {horizon} months.")
    row = matches[0]
    label = MODEL_LABELS[model]
    components = json.loads(row.get("components_json") or "{}")
    weights = json.loads(row.get("weights_json") or "{}")
    if model == "ensemble":
        value = _float(row.get("ensemble_forecast_yoy_pct"))
    else:
        value = _float(components.get(label))
    if value is None:
        raise LookupError(f"No stored {label} forecast is available for {variant} at {horizon} months.")

    metrics = _read_csv(f"{folder}/test_metrics.csv")
    metric = next((item for item in metrics
                   if item.get("horizon_months") == str(horizon) and item.get("model") == label), None)
    if variant == "oecd_long_history_sensitivity":
        series_id = "oecd_india_cpi_yoy"
        target_label = "OECD India CPI sensitivity series"
    else:
        series_id = "cpi_yoy"
        target_label = "MoSPI India CPI 2024-base series"
    calibration = None
    if metric:
        coverage_80 = _float(metric.get("test_coverage80_using_dev_calibration"))
        coverage_95 = _float(metric.get("test_coverage95_using_dev_calibration"))
        calibration = {
            "coverage_80": coverage_80,
            "coverage_95": coverage_95,
            "status": "comparison_period_observed_coverage",
            "model_version": f"{variant}@{row.get('forecast_origin', 'unknown')}",
        }

    metadata = _read_json(f"{folder}/metadata.json")
    target_rows = load_packaged_cpi_target() if variant != "oecd_long_history_sensitivity" else []
    start = (target_rows[0]["date"][:7] if target_rows else metadata.get("target_start"))
    end = (target_rows[-1]["date"][:7] if target_rows else metadata.get("target_end"))
    warnings = [
        f"Stored model forecast from the package's {row.get('forecast_origin', 'recorded')} origin; it is not recomputed from current observations.",
        "The comparison period was inspected during feature-specification selection and is not an independent final holdout.",
        "The target includes 2025 YoY values derived from rounded same-base CPI index levels.",
        "Empirical interval coverage is historical comparison-period coverage, not a guarantee of future coverage.",
    ]
    return {
        "series_id": series_id,
        "model": model,
        "model_label": label,
        "variant": variant,
        "status": "stored_snapshot",
        "mode": "final_model_package_artifact",
        "origin": row.get("forecast_origin"),
        "target_month": row.get("target_month"),
        "horizon_months": horizon,
        "forecasts": [{"step": horizon, "value": value}],
        "component_forecasts": {key: number for key, raw in components.items()
                                 if (number := _float(raw)) is not None},
        "model_weights": {key: number for key, raw in weights.items()
                           if (number := _float(raw)) is not None},
        "intervals": {
            "80": {"lower": _float(row.get("interval80_low")), "upper": _float(row.get("interval80_high"))},
            "95": {"lower": _float(row.get("interval95_low")), "upper": _float(row.get("interval95_high"))},
        },
        "calibration": calibration,
        "source_observations": int(metadata.get("n_months") or metadata.get("data_quality", {}).get("n_observations", 0)),
        "source": target_label,
        "unit": "percent",
        "dataset_start": start,
        "dataset_end": end,
        "package_created_at": metadata.get("created_utc"),
        "warnings": warnings,
    }


def final_model_explainability(model: str, variant: str, horizon: int) -> dict[str, Any]:
    """Return recorded XGBoost SHAP values for the package's latest origin."""
    variant_dir = _variant_dir(variant)
    if model != "xgboost":
        raise LookupError("Stored SHAP values are available only for XGBoost forecasts.")
    if not 1 <= horizon <= 12:
        raise ValueError("horizon must be between 1 and 12 months")
    folder = f"artifacts/{variant_dir}"
    rows = _read_csv(f"{folder}/diagnostics/shap_latest_origin.csv")
    contributions = [
        {"feature": row["feature"], "contribution": value, "unit": "percentage points"}
        for row in rows
        if row.get("horizon_months") == str(horizon)
        and (value := _float(row.get("shap_value_at_latest_origin"))) is not None
    ]
    if not contributions:
        raise LookupError(f"No SHAP values are recorded for {variant} at horizon {horizon} months.")
    contributions.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    forecast_rows = _read_csv(f"{folder}/forecasts.csv")
    forecast_row = next((row for row in forecast_rows if row.get("horizon_months") == str(horizon)), {})
    return {
        "model_version": f"{variant}@{forecast_row.get('forecast_origin', 'unknown')}",
        "method": "shap",
        "contributions": contributions[:20],
        "warnings": [
            "SHAP values describe the recorded XGBoost prediction at the package's stored forecast origin; they are predictive attributions, not causal effects.",
        ],
    }


def final_package_status() -> dict[str, Any]:
    """Return a cheap deployment health indicator without loading model binaries."""
    if not PACKAGE_ROOT.is_dir():
        return {"status": "not_configured"}
    if not (PACKAGE_ROOT / "SHA256SUMS.txt").is_file():
        return {"status": "invalid"}
    return {"status": "configured"}
