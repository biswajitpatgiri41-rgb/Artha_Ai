#!/usr/bin/env python
"""
CPI Forecasting Feature Pipeline.

Builds features for CPI inflation forecasting from the macro monthly table.
Input: data/processed/macro_monthly.parquet
Output: data/processed/cpi_features.parquet + feature manifest

Features created:
- oil_yoy = 100 * brent_price.pct_change(12)
- inr_yoy = 100 * inr_usd.pct_change(12)
- repo_change_1m = repo_rate.diff(1)
- repo_change_3m = repo_rate.diff(3)
- real_policy_rate = repo_rate - cpi_yoy
- month_sin = sin(2*pi*month/12)
- month_cos = cos(2*pi*month/12)
- Lag features (1,2,3,6,12) for: cpi_yoy, food_inflation_yoy, oil_yoy, inr_yoy
- Rolling: cpi_ma_3, cpi_ma_6, oil_vol_6, inr_vol_6
- Targets: target_h1, target_h3, target_h6, target_h12

CRITICAL: No feature at date t may use information from t+1 or later.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.forecasting import CPI_FEATURES_PATH, HORIZONS, LAG_PERIODS


def load_macro_monthly(path: str) -> pd.DataFrame:
    """Load the macro monthly table."""
    p = Path(path)
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    elif p.suffix == ".csv":
        return pd.read_csv(p, parse_dates=["date"])
    else:
        raise ValueError(f"Unsupported file format: {p.suffix}")


def validate_no_leakage(df: pd.DataFrame, feature_cols: list[str], target_cols: list[str]) -> list[str]:
    """
    Validate that no feature uses future information.
    Checks that all features at time t only depend on data up to time t.
    """
    warnings = []
    
    # Check that target columns are shifted (not current values)
    for target in target_cols:
        if target in df.columns:
            # Target should be NaN for the last few rows (shifted forward)
            non_null = df[target].notna().sum()
            total = len(df)
            if non_null == total:
                warnings.append(f"LEAKAGE RISK: {target} has no NaN values - may not be properly shifted")
    
    # Check lag features are properly lagged (should have NaN at start)
    for col in feature_cols:
        if col.startswith(("cpi_yoy_lag_", "food_inflation_yoy_lag_", "oil_yoy_lag_", "inr_yoy_lag_")):
            lag_num = int(col.split("_")[-1])
            expected_nans = lag_num
            actual_nans = df[col].isna().sum()
            if actual_nans < expected_nans:
                warnings.append(f"LEAKAGE RISK: {col} has only {actual_nans} NaN values, expected at least {expected_nans}")
    
    # Check rolling features don't use future
    for col in feature_cols:
        if col in ("cpi_ma_3", "cpi_ma_6"):
            window = int(col.split("_")[-1])
            expected_nans = window - 1
            actual_nans = df[col].isna().sum()
            if actual_nans < expected_nans:
                warnings.append(f"LEAKAGE RISK: {col} has only {actual_nans} NaN values, expected at least {expected_nans}")
        elif col in ("oil_vol_6", "inr_vol_6"):
            window = 6
            expected_nans = window - 1
            actual_nans = df[col].isna().sum()
            if actual_nans < expected_nans:
                warnings.append(f"LEAKAGE RISK: {col} has only {actual_nans} NaN values, expected at least {expected_nans}")
    
    return warnings


def create_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Create all forecasting features from macro monthly data.
    
    Returns:
        DataFrame with features and feature manifest dict.
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    
    # Ensure date is datetime
    df["date"] = pd.to_datetime(df["date"])
    
    feature_manifest = {
        "created_at": datetime.utcnow().isoformat(),
        "source_table": "macro_monthly",
        "transformations": [],
        "features": {},
        "targets": {},
        "leakage_warnings": [],
    }
    
    # ============================================================
    # DERIVED FEATURES (from existing columns)
    # ============================================================
    
    # oil_yoy = 100 * brent_price.pct_change(12)
    if "brent_price" in df.columns:
        df["oil_yoy"] = 100 * df["brent_price"].pct_change(12)
        feature_manifest["transformations"].append({
            "feature": "oil_yoy",
            "formula": "100 * brent_price.pct_change(12)",
            "description": "Brent crude year-over-year percentage change",
            "dependencies": ["brent_price"],
        })
        feature_manifest["features"]["oil_yoy"] = {
            "type": "derived",
            "formula": "100 * brent_price.pct_change(12)",
            "unit": "percent",
        }
    
    # inr_yoy = 100 * inr_usd.pct_change(12)
    if "inr_usd" in df.columns:
        df["inr_yoy"] = 100 * df["inr_usd"].pct_change(12)
        feature_manifest["transformations"].append({
            "feature": "inr_yoy",
            "formula": "100 * inr_usd.pct_change(12)",
            "description": "INR/USD year-over-year percentage change",
            "dependencies": ["inr_usd"],
        })
        feature_manifest["features"]["inr_yoy"] = {
            "type": "derived",
            "formula": "100 * inr_usd.pct_change(12)",
            "unit": "percent",
        }
    
    # repo_change_1m = repo_rate.diff(1)
    if "repo_rate" in df.columns:
        df["repo_change_1m"] = df["repo_rate"].diff(1)
        feature_manifest["transformations"].append({
            "feature": "repo_change_1m",
            "formula": "repo_rate.diff(1)",
            "description": "1-month change in repo rate",
            "dependencies": ["repo_rate"],
        })
        feature_manifest["features"]["repo_change_1m"] = {
            "type": "derived",
            "formula": "repo_rate.diff(1)",
            "unit": "percentage_points",
        }
    
    # repo_change_3m = repo_rate.diff(3)
    if "repo_rate" in df.columns:
        df["repo_change_3m"] = df["repo_rate"].diff(3)
        feature_manifest["transformations"].append({
            "feature": "repo_change_3m",
            "formula": "repo_rate.diff(3)",
            "description": "3-month change in repo rate",
            "dependencies": ["repo_rate"],
        })
        feature_manifest["features"]["repo_change_3m"] = {
            "type": "derived",
            "formula": "repo_rate.diff(3)",
            "unit": "percentage_points",
        }
    
    # real_policy_rate = repo_rate - cpi_yoy
    if "repo_rate" in df.columns and "cpi_yoy" in df.columns:
        df["real_policy_rate"] = df["repo_rate"] - df["cpi_yoy"]
        feature_manifest["transformations"].append({
            "feature": "real_policy_rate",
            "formula": "repo_rate - cpi_yoy",
            "description": "Real policy rate (nominal repo rate minus CPI inflation)",
            "dependencies": ["repo_rate", "cpi_yoy"],
        })
        feature_manifest["features"]["real_policy_rate"] = {
            "type": "derived",
            "formula": "repo_rate - cpi_yoy",
            "unit": "percent",
        }
    
    # ============================================================
    # SEASONALITY FEATURES
    # ============================================================
    
    df["month"] = df["date"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    
    feature_manifest["transformations"].append({
        "feature": "month_sin",
        "formula": "sin(2*pi*month/12)",
        "description": "Seasonal sine encoding",
        "dependencies": ["date"],
    })
    feature_manifest["features"]["month_sin"] = {
        "type": "seasonal",
        "formula": "sin(2*pi*month/12)",
        "unit": "dimensionless",
    }
    
    feature_manifest["transformations"].append({
        "feature": "month_cos",
        "formula": "cos(2*pi*month/12)",
        "description": "Seasonal cosine encoding",
        "dependencies": ["date"],
    })
    feature_manifest["features"]["month_cos"] = {
        "type": "seasonal",
        "formula": "cos(2*pi*month/12)",
        "unit": "dimensionless",
    }
    
    # ============================================================
    # LAG FEATURES
    # ============================================================
    
    lag_features = ["cpi_yoy", "food_inflation_yoy", "oil_yoy", "inr_yoy"]
    
    for base_feature in lag_features:
        if base_feature not in df.columns:
            continue
        for lag in LAG_PERIODS:
            lag_col = f"{base_feature}_lag_{lag}"
            df[lag_col] = df[base_feature].shift(lag)
            feature_manifest["transformations"].append({
                "feature": lag_col,
                "formula": f"{base_feature}.shift({lag})",
                "description": f"{lag}-month lag of {base_feature}",
                "dependencies": [base_feature],
            })
            feature_manifest["features"][lag_col] = {
                "type": "lag",
                "base_feature": base_feature,
                "lag": lag,
                "formula": f"{base_feature}.shift({lag})",
                "unit": feature_manifest["features"].get(base_feature, {}).get("unit", "percent"),
            }
    
    # ============================================================
    # ROLLING FEATURES
    # ============================================================
    
    # cpi_ma_3 = cpi_yoy.rolling(3).mean()
    if "cpi_yoy" in df.columns:
        df["cpi_ma_3"] = df["cpi_yoy"].rolling(3, min_periods=1).mean()
        feature_manifest["transformations"].append({
            "feature": "cpi_ma_3",
            "formula": "cpi_yoy.rolling(3).mean()",
            "description": "3-month moving average of CPI YoY",
            "dependencies": ["cpi_yoy"],
        })
        feature_manifest["features"]["cpi_ma_3"] = {
            "type": "rolling",
            "formula": "cpi_yoy.rolling(3).mean()",
            "unit": "percent",
        }
        
        df["cpi_ma_6"] = df["cpi_yoy"].rolling(6, min_periods=1).mean()
        feature_manifest["transformations"].append({
            "feature": "cpi_ma_6",
            "formula": "cpi_yoy.rolling(6).mean()",
            "description": "6-month moving average of CPI YoY",
            "dependencies": ["cpi_yoy"],
        })
        feature_manifest["features"]["cpi_ma_6"] = {
            "type": "rolling",
            "formula": "cpi_yoy.rolling(6).mean()",
            "unit": "percent",
        }
    
    # oil_vol_6 = oil_yoy.rolling(6).std()
    if "oil_yoy" in df.columns:
        df["oil_vol_6"] = df["oil_yoy"].rolling(6, min_periods=2).std()
        feature_manifest["transformations"].append({
            "feature": "oil_vol_6",
            "formula": "oil_yoy.rolling(6).std()",
            "description": "6-month rolling volatility of oil YoY",
            "dependencies": ["oil_yoy"],
        })
        feature_manifest["features"]["oil_vol_6"] = {
            "type": "rolling",
            "formula": "oil_yoy.rolling(6).std()",
            "unit": "percent",
        }
    
    # inr_vol_6 = inr_yoy.rolling(6).std()
    if "inr_yoy" in df.columns:
        df["inr_vol_6"] = df["inr_yoy"].rolling(6, min_periods=2).std()
        feature_manifest["transformations"].append({
            "feature": "inr_vol_6",
            "formula": "inr_yoy.rolling(6).std()",
            "description": "6-month rolling volatility of INR YoY",
            "dependencies": ["inr_yoy"],
        })
        feature_manifest["features"]["inr_vol_6"] = {
            "type": "rolling",
            "formula": "inr_yoy.rolling(6).std()",
            "unit": "percent",
        }
    
    # ============================================================
    # TARGETS (shifted forward - no leakage)
    # ============================================================
    
    if "cpi_yoy" in df.columns:
        for horizon in HORIZONS:
            months = {"h1": 1, "h3": 3, "h6": 6, "h12": 12}[horizon]
            target_col = f"target_{horizon}"
            df[target_col] = df["cpi_yoy"].shift(-months)
            feature_manifest["transformations"].append({
                "feature": target_col,
                "formula": f"cpi_yoy.shift(-{months})",
                "description": f"CPI YoY target at {months}-month horizon",
                "dependencies": ["cpi_yoy"],
                "is_target": True,
            })
            feature_manifest["targets"][target_col] = {
                "type": "target",
                "horizon_months": months,
                "formula": f"cpi_yoy.shift(-{months})",
                "unit": "percent",
            }
    
    # ============================================================
    # LEAKAGE VALIDATION
    # ============================================================
    
    feature_cols = [c for c in df.columns if c not in ["date", "month"]]
    target_cols = [f"target_{h}" for h in HORIZONS]
    
    leakage_warnings = validate_no_leakage(df, feature_cols, target_cols)
    feature_manifest["leakage_warnings"] = leakage_warnings
    
    if leakage_warnings:
        print("LEAKAGE WARNINGS:")
        for w in leakage_warnings:
            print(f"  - {w}")
    else:
        print("Leakage validation: PASSED")
    
    # Drop helper column
    df = df.drop(columns=["month"])
    
    return df, feature_manifest


def save_outputs(df: pd.DataFrame, manifest: dict):
    """Save features to Parquet and manifest to JSON."""
    output_dir = Path(CPI_FEATURES_PATH).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_path = Path(CPI_FEATURES_PATH)
    
    # Save Parquet
    parquet_path = base_path.with_suffix(".parquet")
    df.to_parquet(parquet_path, index=False)
    print(f"Saved features: {parquet_path}")
    
    # Save CSV
    csv_path = base_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")
    
    # Save manifest
    manifest_path = base_path.with_suffix(".json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"Saved manifest: {manifest_path}")


def print_feature_summary(df: pd.DataFrame, manifest: dict):
    """Print feature summary."""
    print("\n" + "=" * 80)
    print("FEATURE PIPELINE SUMMARY")
    print("=" * 80)
    print(f"Rows:              {len(df)}")
    print(f"Date range:        {df['date'].min()} to {df['date'].max()}")
    print(f"Total features:    {len([c for c in df.columns if c != 'date'])}")
    print(f"Feature columns:   {[c for c in df.columns if c != 'date']}")
    print()
    
    # Missing data
    print("Missing data per feature (top 20):")
    missing = df.isna().sum().sort_values(ascending=False)
    for col, count in missing.head(20).items():
        if count > 0:
            pct = count / len(df) * 100
            print(f"  {col:<30} {count:>5} / {len(df):<5} ({pct:>5.1f}%)")
    
    if manifest["leakage_warnings"]:
        print("\nLEAKAGE WARNINGS (must fix before training):")
        for w in manifest["leakage_warnings"]:
            print(f"  - {w}")
    else:
        print("\nLeakage validation: ALL CLEAR")


def main():
    """Main entry point."""
    print("Building CPI forecasting features...")
    print("-" * 80)
    
    macro_path = "data/processed/macro_monthly.parquet"
    if not Path(macro_path).exists():
        macro_path = "data/processed/macro_monthly.csv"
        if not Path(macro_path).exists():
            print(f"Error: Macro monthly table not found at {macro_path}")
            print("Run scripts/build_macro_monthly.py first")
            sys.exit(1)
    
    try:
        df = load_macro_monthly(macro_path)
        print(f"Loaded macro monthly: {len(df)} rows, {len(df.columns)} columns")
        
        df_features, manifest = create_features(df)
        save_outputs(df_features, manifest)
        print_feature_summary(df_features, manifest)
        print("\nFeature pipeline completed successfully.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()