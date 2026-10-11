#!/usr/bin/env python3
"""Validate source-derived datasets and serialized India CPI model artifacts."""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from india_feature_engineering import build_feature_frame, load_panel  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    model_manifest_path = ROOT / "models/model_artifact_manifest.json"
    model_manifest = json.loads(model_manifest_path.read_text(encoding="utf-8"))
    artifact_checks = []
    loaded = {}
    for record in model_manifest["artifacts"]:
        path = ROOT / record["path"]
        exists = path.is_file()
        hash_ok = exists and sha256(path) == record["sha256"]
        try:
            with path.open("rb") as stream:
                loaded[path.name] = pickle.load(stream)
            loads = True
        except Exception as exc:
            loads = False
            artifact_checks.append({"path": record["path"], "error": f"{type(exc).__name__}: {exc}"})
        if exists and path.stat().st_size != record["bytes"]:
            hash_ok = False
        if not exists or not hash_ok or not loads:
            artifact_checks.append({"path": record["path"], "exists": exists, "hash_ok": hash_ok, "loads": loads})

    panel = load_panel(str(ROOT / "data/processed/india_cpi_monthly_panel.csv"))
    features = build_feature_frame(panel)
    target = pd.read_csv(ROOT / "data/processed/india_headline_cpi_target.csv")
    long_path = ROOT / "data/processed/india_cpi_observations_long.csv"
    long_rows = sum(1 for _ in long_path.open(encoding="utf-8")) - 1
    target_observed = int(target["headline_cpi_yoy_pct"].notna().sum())
    expected_periods = pd.period_range("2013-01", "2025-12", freq="M")
    data_ok = (
        len(panel) == 156 and panel.index.equals(expected_periods)
        and target_observed == 142 and str(target.loc[target["headline_cpi_yoy_pct"].notna(), "period"].iloc[0]) == "2014-01"
        and str(target.loc[target["headline_cpi_yoy_pct"].notna(), "period"].iloc[-1]) == "2025-12"
        and long_rows == 12948
    )

    best = loaded.get("best_trained_model.pkl")
    if best is None:
        best_prediction_checks = False
    else:
        origin = features.index.max()
        best_prediction_checks = True
        for horizon_text, spec in best["horizons"].items():
            horizon = int(horizon_text)
            estimator = spec["estimator"]
            if best["selected_model_family"].startswith("ARIMA"):
                predicted = np.asarray(estimator.get_forecast(steps=horizon).predicted_mean, dtype=float)[-1]
            else:
                row = features.loc[[origin]].reindex(columns=spec["feature_columns"])
                predicted = float(estimator.predict(row)[0])
            if not np.isfinite(predicted):
                best_prediction_checks = False

    result = {
        "status": "PASS" if data_ok and not artifact_checks and best_prediction_checks else "FAIL",
        "processed_data_checks": {
            "monthly_panel_rows": int(len(panel),),
            "monthly_panel_start": str(panel.index.min()),
            "monthly_panel_end": str(panel.index.max()),
            "target_observed_count": target_observed,
            "long_observation_count": int(long_rows),
            "expected_checks_passed": bool(data_ok),
        },
        "model_artifacts_expected": len(model_manifest["artifacts"]),
        "model_artifacts_loaded": len(loaded),
        "artifact_errors": artifact_checks,
        "selected_model_family": best.get("selected_model_family") if best else None,
        "selected_model_prediction_checks_passed": bool(best_prediction_checks),
        "scope_note": "Forecast outputs use the discontinued 2012=100 target and are not comparable to the current 2024=100 series.",
    }
    out = ROOT / "reports/artifact_validation.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
