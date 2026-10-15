from __future__ import annotations

import json
import warnings
import zipfile

import pytest
from fastapi import HTTPException

from app.api.research_routes import get_p2_forecast
from app.models import p2_cpi_benchmark as p2
from scripts import import_p2_cpi_bundle as bundle_importer


def test_p2_training_panel_has_expected_lagged_observations():
    panel = p2._training_panel()

    assert len(panel) == 160
    assert len(panel.columns) == 14
    assert panel.index[0].strftime("%Y-%m") == "2013-01"
    assert panel.index[-1].strftime("%Y-%m") == "2026-04"


def test_p2_future_features_use_only_observed_lags():
    raw = p2._load_raw()
    features = p2._future_features(raw)

    assert features.index[0].strftime("%Y-%m") == "2026-05"
    assert features.iloc[0]["iip_lag1"] == raw["iip"].iloc[-1]
    assert features.iloc[0]["cpi_lag1"] == raw[p2.TARGET].iloc[-1]
    assert features.iloc[0]["cpi_lag2"] == raw[p2.TARGET].iloc[-2]
    assert features.iloc[0]["m3_lag12"] == raw["m3"].iloc[-12]


def test_p2_registry_reports_models_not_imported(tmp_path, monkeypatch):
    monkeypatch.setattr(p2, "ARTIFACTS", tmp_path / "artifacts")

    registry = p2.p2_model_registry()

    assert registry["status"] == "dataset_available_models_not_imported"
    assert registry["training_observations"] == 160
    assert registry["models"]["p2_persistence"] == "available"
    assert set(registry["models"][model] for model in ("p2_arima", "p2_arimax", "p2_elasticnet", "p2_xgboost")) == {"not_imported"}
    assert registry["metrics"] == []


def test_p2_forecast_rejects_unsupported_horizon():
    try:
        p2.p2_forecast("p2_arima", horizon=3)
    except ValueError as exc:
        assert "one-month-ahead" in str(exc)
    else:
        raise AssertionError("P2 benchmark must reject horizons beyond one month.")


def test_p2_persistence_forecast_works_without_model_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(p2, "ARTIFACTS", tmp_path / "artifacts")

    forecast = p2.p2_forecast("p2_persistence")

    assert forecast["target_month"] == "2026-05"
    assert forecast["forecasts"][0]["value"] == p2._load_raw()[p2.TARGET].iloc[-1]


def test_p2_forecast_route_reports_missing_model_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(p2, "ARTIFACTS", tmp_path / "artifacts")

    with pytest.raises(HTTPException) as error:
        get_p2_forecast()

    assert error.value.status_code == 409
    assert error.value.detail["status"] == "model_not_ready"


def test_p2_bundle_import_checks_metadata_and_source_license(tmp_path):
    metadata = {
        "source_commit": bundle_importer.EXPECTED_COMMIT,
        "dataset_sha256": bundle_importer.EXPECTED_DATASET_SHA256,
        "source_license": "MIT (see LICENSE-p2-india-cpi-forecasting.txt)",
        "target": "cpi_inflation",
        "validation": {"test_observations": 52},
        "models": ["arima_300", "arimax_300", "elasticnet", "xgboost"],
    }
    bundle = tmp_path / "p2_bundle.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        for name in bundle_importer.EXPECTED_FILES:
            if name == "training_metadata.json":
                content = json.dumps(metadata).encode()
            elif name == "LICENSE-p2-india-cpi-forecasting.txt":
                content = (bundle_importer.DATA_FILE.parent / "LICENSE").read_bytes()
            else:
                content = b"fixture"
            archive.writestr(name, content)

    staging = tmp_path / "staging"
    staging.mkdir()
    bundle_importer._validate_bundle(bundle, staging)

    assert (staging / "training_metadata.json").is_file()
    assert (staging / "arima_300.joblib").is_file()


@pytest.mark.skipif(
    not (p2.ARTIFACTS / "retrained_models_manifest.json").is_file(),
    reason="Compatible P2 artifacts have not been generated in this checkout.",
)
def test_p2_retrained_arimax_converges_on_every_origin_and_forecasts():
    manifest = p2._retrained_manifest()

    assert manifest["arimax"]["final_fit_converged"] is True
    assert manifest["arimax"]["converged_at_all_walk_forward_origins"] is True
    assert len(manifest["arimax"]["walk_forward_convergence"]) == 52
    assert all(item["converged"] for item in manifest["arimax"]["walk_forward_convergence"])
    assert p2.p2_model_registry()["models"]["p2_arimax"] == "available"
    assert p2.p2_forecast("p2_arimax")["forecasts"][0]["value"] == pytest.approx(
        manifest["smoke_test_predictions"]["p2_arimax"]
    )


@pytest.mark.skipif(
    not (p2.ARTIFACTS / "xgboost_native.json").is_file(),
    reason="Native P2 XGBoost artifact has not been generated in this checkout.",
)
def test_p2_xgboost_uses_native_serialization_without_pickle_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        forecast = p2.p2_forecast("p2_xgboost")

    assert forecast["forecasts"][0]["value"] == pytest.approx(
        p2._retrained_manifest()["smoke_test_predictions"]["p2_xgboost"]
    )
    assert not any("serialized model" in str(item.message).lower() for item in caught)
