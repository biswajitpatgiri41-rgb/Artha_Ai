#!/usr/bin/env python3
"""Run 1/3/6-month forecasts from the packaged best learned model.

The package is trained on MoSPI's discontinued 2012=100 CPI target through
December 2025. Forecasts from this script are projections of that old-base
series and are not directly comparable with the new 2024=100 CPI.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from india_feature_engineering import build_feature_frame, load_panel  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", default=str(ROOT / "data/processed/india_cpi_monthly_panel.csv"))
    parser.add_argument("--model", default=str(ROOT / "models/best_trained_model.pkl"))
    parser.add_argument("--output", default=str(ROOT / "reports/archived_2012_base_forecasts.csv"))
    args = parser.parse_args()

    panel = load_panel(args.panel)
    features = build_feature_frame(panel)
    with open(args.model, "rb") as f:
        artifact = pickle.load(f)
    origin = features.index.max()
    rows = []
    family = artifact["selected_model_family"]
    for horizon_text, model_spec in artifact["horizons"].items():
        horizon = int(horizon_text)
        estimator = model_spec["estimator"]
        if family.startswith("ARIMA"):
            forecast = float(np.asarray(estimator.get_forecast(steps=horizon).predicted_mean, dtype=float)[-1])
        else:
            x = features.loc[[origin]].reindex(columns=model_spec["feature_columns"])
            forecast = float(estimator.predict(x)[0])
        rows.append({
            "model_family": family,
            "forecast_origin_last_observed_month": str(origin),
            "forecast_issue_month": str(origin + 1),
            "horizon_months": horizon,
            "forecast_target_month": str(origin + horizon),
            "forecast_yoy_pct_old_2012_base": forecast,
            "target_base": "2012=100 (discontinued after 2025-12)",
            "comparable_to_2024_base_series": False,
            "model_target_cutoff": artifact["training_target_cutoff"],
        })
    output = pd.DataFrame(rows).sort_values("horizon_months")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    print("WARNING: these are old 2012-base projections; do not interpret them as forecasts of the new 2024-base CPI without recalibration.")
    print(output.to_string(index=False))
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
