#!/usr/bin/env python3
"""Feature construction for India monthly CPI direct forecasts.

Features are indexed by the last observed month (forecast origin). Each model
uses only values dated at or before that origin. The target is MoSPI's published
headline YoY rate; exogenous category-index features retain their older Kaggle /
data.gov.in source vintage and are never interpolated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_COL = "headline_cpi_yoy_pct"

CATEGORY_INDEX_COLUMNS = {
    "combined_food_yoy": "combined__food_and_beverages_index_2012_100",
    "combined_fuel_yoy": "combined__fuel_and_light_index_2012_100",
    "combined_housing_yoy": "combined__housing_index_2012_100",
    "combined_transport_yoy": "combined__transport_and_communication_index_2012_100",
    "combined_clothing_yoy": "combined__clothing_and_footwear_index_2012_100",
    "rural_general_archive_yoy": "rural__general_index_index_2012_100_archive_snapshot",
    "urban_general_archive_yoy": "urban__general_index_index_2012_100_archive_snapshot",
}


def load_panel(path: str) -> pd.DataFrame:
    panel = pd.read_csv(path)
    if "period" not in panel or TARGET_COL not in panel:
        raise ValueError(f"Expected period and {TARGET_COL} columns")
    panel["period"] = pd.PeriodIndex(panel["period"], freq="M")
    panel = panel.sort_values("period").set_index("period")
    if panel.index.has_duplicates:
        raise ValueError("Monthly panel contains duplicate periods")
    return panel


def build_feature_frame(panel: pd.DataFrame) -> pd.DataFrame:
    """Return a month-indexed feature table, never using future observations."""
    if "period" in panel.columns:
        frame = panel.copy()
        frame["period"] = pd.PeriodIndex(frame["period"], freq="M")
        frame = frame.sort_values("period").set_index("period")
    else:
        frame = panel.copy()
        if not isinstance(frame.index, pd.PeriodIndex):
            frame.index = pd.PeriodIndex(frame.index, freq="M")
        frame = frame.sort_index()
    if frame.index.has_duplicates:
        raise ValueError("Monthly panel contains duplicate periods")
    if TARGET_COL not in frame.columns:
        raise ValueError(f"Panel does not include {TARGET_COL}")

    target = pd.to_numeric(frame[TARGET_COL], errors="coerce").astype(float)
    features = pd.DataFrame(index=frame.index)

    for lag in [0, 1, 2, 3, 6, 12]:
        features[f"headline_yoy_lag_{lag}"] = target.shift(lag)
    for window in [3, 6, 12]:
        # Mean is over available observed target values inside the trailing
        # window. It does not fill or alter the underlying target series.
        features[f"headline_yoy_trailing_mean_{window}"] = target.rolling(
            window=window, min_periods=max(1, window // 2)
        ).mean()
    features["headline_yoy_change_1m"] = target - target.shift(1)
    features["headline_yoy_trailing_std_6"] = target.rolling(window=6, min_periods=3).std()

    for feature_name, index_col in CATEGORY_INDEX_COLUMNS.items():
        if index_col in frame.columns:
            index_level = pd.to_numeric(frame[index_col], errors="coerce").astype(float)
            features[feature_name] = 100.0 * (index_level / index_level.shift(12) - 1.0)
        else:
            # Keep a stable schema when an optional exogenous column is absent;
            # train-only pipeline imputers handle these null feature values.
            features[feature_name] = np.nan

    month = frame.index.month.to_numpy()
    features["month_sin"] = np.sin(2.0 * np.pi * month / 12.0)
    features["month_cos"] = np.cos(2.0 * np.pi * month / 12.0)
    return features.astype(float)
