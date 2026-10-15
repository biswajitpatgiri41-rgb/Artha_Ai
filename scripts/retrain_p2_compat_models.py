"""Retrain the P2 ARIMAX and XGBoost models with stable numerical/model formats."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
import statsmodels
import xgboost
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.arima.model import ARIMA
from xgboost import XGBRegressor

from app.models import p2_cpi_benchmark as p2


TEST_START = pd.Timestamp("2022-01-01")
REDUNDANT_ARIMAX_FEATURE = "term_spread_lag1"
ARIMAX_OUTPUT = "arimax_300_converged.joblib"
ARIMAX_SCALER_OUTPUT = "arimax_scaler.json"
XGBOOST_OUTPUT = "xgboost_native.json"
MANIFEST_OUTPUT = "retrained_models_manifest.json"


def _xgboost_estimator() -> XGBRegressor:
    return XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        max_depth=2,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=10.0,
        random_state=42,
        n_jobs=2,
        verbosity=0,
    )


def _fit_arimax(
    train: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[object, StandardScaler, np.ndarray, int]:
    scaler = StandardScaler().fit(train[feature_columns])
    scaled_features = scaler.transform(train[feature_columns])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.filterwarnings("ignore", message="No frequency information was provided")
        fitted = ARIMA(
            train[p2.TARGET],
            order=(3, 0, 0),
            exog=scaled_features,
        ).fit(
            method="statespace",
            method_kwargs={"method": "lbfgs", "maxiter": 1000, "disp": 0},
        )
    convergence_warnings = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]
    retvals = getattr(fitted, "mle_retvals", {})
    converged = isinstance(retvals, dict) and bool(retvals.get("converged", False))
    if not converged or convergence_warnings:
        raise RuntimeError(
            "ARIMAX fit did not converge cleanly: "
            f"retvals={retvals!r}, warnings={convergence_warnings!r}"
        )
    return fitted, scaler, scaled_features, int(retvals.get("iterations", 0))


def _metric_row(name: str, actual: list[float], predicted: list[float]) -> dict[str, object]:
    return {
        "model": name,
        "test_start": "2022-01-01",
        "test_end": "2026-04-01",
        "n_test": len(actual),
        "mae_percentage_points": float(mean_absolute_error(actual, predicted)),
        "rmse_percentage_points": float(np.sqrt(mean_squared_error(actual, predicted))),
    }


def _validate_training_artifacts(
    feature_columns: list[str],
    arimax_features: list[str],
    raw: pd.DataFrame,
    staging: Path,
    expected_origins: int,
) -> dict[str, object]:
    arimax = joblib.load(staging / ARIMAX_OUTPUT)
    scaler_metadata = json.loads((staging / ARIMAX_SCALER_OUTPUT).read_text(encoding="utf-8"))
    if not arimax.mle_retvals.get("converged", False):
        raise RuntimeError("Saved ARIMAX artifact failed its reload convergence check.")
    future = p2._future_features(raw).reindex(columns=arimax_features)
    scaled_future = (future.to_numpy() - np.asarray(scaler_metadata["mean"])) / np.asarray(
        scaler_metadata["scale"]
    )
    arimax_prediction = float(arimax.forecast(steps=1, exog=scaled_future).iloc[0])

    booster = xgboost.Booster()
    booster.load_model(staging / XGBOOST_OUTPUT)
    xgb_prediction = float(
        booster.predict(
            xgboost.DMatrix(
                p2._future_features(raw).reindex(columns=feature_columns),
                feature_names=feature_columns,
            )
        )[0]
    )
    if not np.isfinite([arimax_prediction, xgb_prediction]).all():
        raise RuntimeError("A saved model returned a non-finite smoke-test prediction.")

    manifest_path = staging / MANIFEST_OUTPUT
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["smoke_test_predictions"] = {
        "p2_arimax": arimax_prediction,
        "p2_xgboost": xgb_prediction,
    }
    manifest["artifact_checks"] = {
        "arimax_reload_converged": True,
        "xgboost_native_json_reload": True,
        "walk_forward_origins": expected_origins,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def retrain(force: bool = False) -> dict[str, object]:
    raw = p2._load_raw()
    panel = p2._training_panel()
    feature_columns = list(panel.columns.drop(p2.TARGET))
    arimax_features = [
        column for column in feature_columns if column != REDUNDANT_ARIMAX_FEATURE
    ]
    if len(arimax_features) != len(feature_columns) - 1:
        raise ValueError(
            f"Expected the redundant feature {REDUNDANT_ARIMAX_FEATURE!r} exactly once."
        )
    origins = panel.index[panel.index >= TEST_START]
    if len(origins) != 52:
        raise ValueError(f"Expected 52 evaluation origins; found {len(origins)}.")

    arimax_actual: list[float] = []
    arimax_predictions: list[float] = []
    xgb_actual: list[float] = []
    xgb_predictions: list[float] = []
    origin_convergence: list[dict[str, object]] = []

    for date in origins:
        train = panel.loc[panel.index < date]
        test = panel.loc[[date]]
        fitted_arimax, scaler, _, iterations = _fit_arimax(train, arimax_features)
        arimax_test = scaler.transform(test[arimax_features])
        prediction = float(fitted_arimax.forecast(steps=1, exog=arimax_test).iloc[0])
        if not np.isfinite(prediction):
            raise RuntimeError(f"ARIMAX returned a non-finite prediction at {date:%Y-%m}.")
        arimax_actual.append(float(test[p2.TARGET].iloc[0]))
        arimax_predictions.append(prediction)
        origin_convergence.append(
            {"date": date.strftime("%Y-%m"), "converged": True, "iterations": iterations}
        )

        xgb = _xgboost_estimator()
        xgb.fit(train[feature_columns], train[p2.TARGET])
        xgb_prediction = float(xgb.predict(test[feature_columns])[0])
        if not np.isfinite(xgb_prediction):
            raise RuntimeError(f"XGBoost returned a non-finite prediction at {date:%Y-%m}.")
        xgb_actual.append(float(test[p2.TARGET].iloc[0]))
        xgb_predictions.append(xgb_prediction)

    final_arimax, final_scaler, _, final_iterations = _fit_arimax(
        panel, arimax_features
    )
    final_xgb = _xgboost_estimator()
    final_xgb.fit(panel[feature_columns], panel[p2.TARGET])

    manifest: dict[str, object] = {
        "source_commit": p2.EXPECTED_COMMIT,
        "dataset_sha256": p2._dataset_hash(),
        "retraining_method": (
            "Expanding one-step walk-forward; ARIMAX uses standardized non-redundant "
            "lagged features, XGBoost uses the original 13-feature panel."
        ),
        "test_start": origins.min().strftime("%Y-%m"),
        "test_end": origins.max().strftime("%Y-%m"),
        "test_observations": int(len(origins)),
        "arimax": {
            "order": [3, 0, 0],
            "optimizer": "lbfgs",
            "max_iterations": 1000,
            "converged_at_all_walk_forward_origins": len(origin_convergence) == len(origins),
            "walk_forward_convergence": origin_convergence,
            "final_fit_converged": bool(final_arimax.mle_retvals.get("converged", False)),
            "final_fit_iterations": final_iterations,
            "feature_columns": arimax_features,
            "removed_redundant_feature": REDUNDANT_ARIMAX_FEATURE,
            "removed_feature_reason": (
                "term_spread_lag1 is exactly derived from gsec_10yr_lag1 minus "
                "tbill_91d_lag1, making the original design matrix rank deficient."
            ),
        },
        "xgboost": {
            "artifact_format": "XGBoost native JSON",
            "feature_columns": feature_columns,
            "parameters": {
                "n_estimators": 100,
                "max_depth": 2,
                "learning_rate": 0.03,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 10.0,
                "random_state": 42,
            },
        },
        "metrics": [
            _metric_row("ARIMAX(3,0,0)", arimax_actual, arimax_predictions),
            _metric_row("XGBoost", xgb_actual, xgb_predictions),
        ],
        "versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "statsmodels": statsmodels.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
        },
    }
    if not final_arimax.mle_retvals.get("converged", False):
        raise RuntimeError("The final ARIMAX fit did not converge; artifacts were not published.")

    p2.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    destinations = [
        p2.ARTIFACTS / ARIMAX_OUTPUT,
        p2.ARTIFACTS / ARIMAX_SCALER_OUTPUT,
        p2.ARTIFACTS / XGBOOST_OUTPUT,
        p2.ARTIFACTS / MANIFEST_OUTPUT,
    ]
    existing = [path.name for path in destinations if path.exists()]
    if existing and not force:
        raise FileExistsError(
            f"Refusing to overwrite retrained artifacts {existing}; use --force to replace them."
        )
    with tempfile.TemporaryDirectory(prefix=".p2-retrain-", dir=p2.ARTIFACTS) as temp_dir:
        staging = Path(temp_dir)
        joblib.dump(final_arimax, staging / ARIMAX_OUTPUT)
        (staging / ARIMAX_SCALER_OUTPUT).write_text(
            json.dumps(
                {
                    "feature_columns": arimax_features,
                    "mean": final_scaler.mean_.tolist(),
                    "scale": final_scaler.scale_.tolist(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        final_xgb.save_model(staging / XGBOOST_OUTPUT)
        (staging / MANIFEST_OUTPUT).write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        _validate_training_artifacts(
            feature_columns, arimax_features, raw, staging, len(origins)
        )
        for name in (ARIMAX_OUTPUT, ARIMAX_SCALER_OUTPUT, XGBOOST_OUTPUT, MANIFEST_OUTPUT):
            os.replace(staging / name, p2.ARTIFACTS / name)

    return json.loads((p2.ARTIFACTS / MANIFEST_OUTPUT).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace previously generated compatible-model artifacts.",
    )
    args = parser.parse_args()
    manifest = retrain(force=args.force)
    print("P2 ARIMAX converged at all walk-forward origins:", manifest["arimax"]["converged_at_all_walk_forward_origins"])
    print("P2 final ARIMAX fit converged:", manifest["arimax"]["final_fit_converged"])
    print("P2 XGBoost saved as native JSON:", p2.ARTIFACTS / XGBOOST_OUTPUT)
    print("Walk-forward metrics:", manifest["metrics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
