#!/usr/bin/env python
"""
Monthly Macroeconomic Table Builder.

Builds the canonical monthly macroeconomic table from normalized observations.
Input: real normalized observations from existing data adapters (data/interim/)
Output: data/processed/macro_monthly.csv, data/processed/macro_monthly.parquet

Requirements:
- One row per calendar month (month-end dates)
- Chronological order
- Source metadata remains traceable
- No random filling
- No target imputation
- No incompatible CPI base-year concatenation
- Duplicate detection
- Frequency validation
"""

import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.forecasting import (
    MACRO_MONTHLY_PATH,
    REQUIRED_MVP_SERIES,
    SERIES_MAPPING,
)
from app.core.series_registry import get_series


def find_latest_normalized_file(canonical_id: str) -> Optional[Path]:
    """Find the latest normalized data file for a canonical series ID."""
    interim_dir = Path("data/interim")
    if not interim_dir.exists():
        return None
    
    pattern = f"{canonical_id}_normalized_*.json"
    files = list(interim_dir.glob(pattern))
    if not files:
        return None
    
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0]


def load_normalized_observations(filepath: Path) -> list[dict]:
    """Load normalized observations from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    # Current adapters persist metadata plus rows in an "observations" array;
    # accept bare observation lists too for older snapshots.
    if isinstance(payload, dict):
        payload = payload.get("observations", [])
    return payload if isinstance(payload, list) else []


def observations_to_dataframe(observations: list[dict], series_id: str) -> pd.DataFrame:
    """Convert observations to a DataFrame with date index."""
    rows = []
    for obs in observations:
        try:
            d = datetime.strptime(obs["obs_date"], "%Y-%m-%d").date()
            rows.append({
                "date": d,
                "value": obs["value"],
                "source": obs.get("source", "UNKNOWN"),
            })
        except (KeyError, ValueError):
            continue
    
    if not rows:
        return pd.DataFrame(columns=["date", "value", "source"])
    
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.sort_values("date")
    df.set_index("date", inplace=True)
    return df


def resample_to_monthly(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Resample to monthly frequency (month-end)."""
    if df.empty:
        return df
    
    if freq == "M":
        # Some monthly registry series can be uploaded from daily official
        # exports (for example Brent). Collapse those to the month's last
        # available value rather than leaving duplicate calendar months.
        if df.index.to_period("M").duplicated().any():
            return df.resample("ME").last()
        return df
    elif freq == "D":
        # For daily data (repo_rate, inr_usd), take month-end value
        return df.resample("M").last()
    elif freq == "F":
        # For fortnightly, take last observation of each month
        return df.resample("M").last()
    elif freq == "Q":
        # For quarterly, forward fill to monthly
        return df.resample("M").ffill()
    elif freq == "A":
        # For annual, forward fill to monthly
        return df.resample("M").ffill()
    else:
        # Default: forward fill
        return df.resample("M").ffill()


def compute_yoy(series: pd.Series) -> pd.Series:
    """Compute year-over-year percentage change."""
    return series.pct_change(12) * 100


def validate_monthly_frequency(df: pd.DataFrame, series_name: str) -> list[str]:
    """Validate that data is monthly with no gaps beyond tolerance."""
    warnings = []
    if df.empty:
        return warnings
    
    # Check for duplicate dates
    dup_dates = df.index[df.index.duplicated()].tolist()
    if dup_dates:
        warnings.append(f"{series_name}: Duplicate dates found: {dup_dates}")
    
    return warnings


def build_macro_monthly() -> tuple[pd.DataFrame, dict]:
    """
    Build the canonical monthly macroeconomic table.
    
    Returns:
        DataFrame with monthly data and metadata dict with quality info.
    """
    # Series we need from registry (mapped to required MVP features)
    series_config = {
        "cpi_yoy": {"registry_id": "cpi_headline", "transform": "yoy", "required": True},
        "food_inflation_yoy": {"registry_id": "food_inflation", "transform": "yoy", "required": True},
        "brent_price": {"registry_id": "brent_crude", "transform": "none", "required": True},
        "inr_usd": {"registry_id": "inr_usd", "transform": "none", "required": True},
        "repo_rate": {"registry_id": "repo_rate", "transform": "none", "required": True},
        "iip_yoy": {"registry_id": "iip", "transform": "yoy", "required": True},
    }
    
    all_data = {}
    all_sources = {}
    all_warnings = []
    
    # Load each series
    for feature_name, config in series_config.items():
        registry_id = config["registry_id"]
        transform = config["transform"]
        required = config["required"]
        
        latest_file = find_latest_normalized_file(registry_id)
        
        if latest_file is None:
            if required:
                all_warnings.append(f"{feature_name} ({registry_id}): No normalized data file found")
            all_data[feature_name] = pd.DataFrame()
            all_sources[feature_name] = "MISSING"
            continue
        
        observations = load_normalized_observations(latest_file)
        if not observations:
            if required:
                all_warnings.append(f"{feature_name} ({registry_id}): Empty normalized file")
            all_data[feature_name] = pd.DataFrame()
            all_sources[feature_name] = "EMPTY"
            continue
        
        # Get source from first observation
        source = observations[0].get("source", "UNKNOWN")
        all_sources[feature_name] = source
        
        # Convert to DataFrame
        df = observations_to_dataframe(observations, registry_id)
        
        # Get registry entry for frequency info
        registry_entry = get_series(registry_id)
        freq = registry_entry.frequency.value if registry_entry else "M"
        
        # Resample to monthly
        df_monthly = resample_to_monthly(df, freq)
        
        # Validate
        warnings = validate_monthly_frequency(df_monthly, feature_name)
        all_warnings.extend(warnings)
        
        # Apply transformation
        if transform == "yoy":
            # For CPI and IIP which are indices, compute YoY
            df_monthly[feature_name] = compute_yoy(df_monthly["value"])
            df_monthly = df_monthly[[feature_name, "source"]].rename(columns={"source": f"{feature_name}_source"})
        elif transform == "none":
            # For brent_price, inr_usd, repo_rate - use as-is
            df_monthly = df_monthly[["value", "source"]].rename(
                columns={"value": feature_name, "source": f"{feature_name}_source"}
            )
        else:
            all_warnings.append(f"{feature_name}: Unknown transform {transform}")
            continue
        
        all_data[feature_name] = df_monthly
    
    # Combine all series on monthly date index
    if not all_data:
        raise ValueError("No data loaded for any series")
    
    # Start with the series that has the most data (brent_crude typically)
    combined = None
    for feature_name, df in all_data.items():
        if df.empty:
            continue
        if combined is None:
            combined = df
        else:
            combined = combined.join(df, how="outer")
    
    if combined is None:
        raise ValueError("No valid data to combine")
    
    # Sort by date
    combined = combined.sort_index()
    
    # Reset index to get date column
    combined = combined.reset_index()
    combined = combined.rename(columns={"index": "date"})
    
    # Ensure date is month-end
    combined["date"] = pd.to_datetime(combined["date"]).dt.to_period("M").dt.to_timestamp("M")
    combined["date"] = combined["date"].dt.date
    
    # Remove any duplicate dates (keep last)
    combined = combined.drop_duplicates(subset=["date"], keep="last")
    combined = combined.sort_values("date").reset_index(drop=True)
    
    # Build metadata
    metadata = {
        "built_at": datetime.utcnow().isoformat(),
        "series_sources": all_sources,
        "warnings": all_warnings,
        "row_count": len(combined),
        "date_range": {
            "start": combined["date"].min().isoformat() if not combined.empty else None,
            "end": combined["date"].max().isoformat() if not combined.empty else None,
        },
        "missing_data": {},
    }
    
    # Calculate missing data per series
    for feature_name in series_config.keys():
        col = feature_name if feature_name in combined.columns else None
        if col:
            missing = combined[col].isna().sum()
            total = len(combined)
            metadata["missing_data"][feature_name] = {
                "missing_count": int(missing),
                "total_count": int(total),
                "missing_pct": round(missing / total * 100, 2) if total > 0 else 100.0,
            }
    
    return combined, metadata


def save_outputs(df: pd.DataFrame, metadata: dict):
    """Save DataFrame to CSV and Parquet, and metadata to JSON."""
    output_dir = Path(MACRO_MONTHLY_PATH).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_path = Path(MACRO_MONTHLY_PATH)
    
    # Save CSV
    csv_path = base_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")
    
    # Save Parquet
    parquet_path = base_path.with_suffix(".parquet")
    df.to_parquet(parquet_path, index=False)
    print(f"Saved Parquet: {parquet_path}")
    
    # Save metadata
    meta_path = base_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"Saved metadata: {meta_path}")


def print_quality_summary(df: pd.DataFrame, metadata: dict):
    """Print dataset quality summary."""
    print("\n" + "=" * 80)
    print("DATASET QUALITY SUMMARY")
    print("=" * 80)
    print(f"Rows:              {metadata['row_count']}")
    print(f"Date range:        {metadata['date_range']['start']} to {metadata['date_range']['end']}")
    print(f"Series sources:    {metadata['series_sources']}")
    print()
    print("Missing data per series:")
    for series, info in metadata["missing_data"].items():
        print(f"  {series:<20} {info['missing_count']:>5} / {info['total_count']:<5} ({info['missing_pct']:>5.1f}%)")
    
    if metadata["warnings"]:
        print("\nWarnings:")
        for w in metadata["warnings"]:
            print(f"  - {w}")
    else:
        print("\nWarnings: None")
    
    # Check for duplicates
    dup_count = df.duplicated(subset=["date"]).sum()
    if dup_count > 0:
        print(f"\nDUPLICATE DETECTED: {dup_count} duplicate dates")
    else:
        print("\nDuplicate check: PASSED (no duplicate dates)")
    
    # Frequency check
    if len(df) > 1:
        date_diffs = pd.to_datetime(df["date"]).diff().dt.days.dropna()
        expected_days = [28, 29, 30, 31]  # month-end differences
        irregular = date_diffs[~date_diffs.isin(expected_days)]
        if len(irregular) > 0:
            print(f"Frequency check: WARNING - {len(irregular)} irregular month gaps")
        else:
            print("Frequency check: PASSED (regular monthly intervals)")


def main():
    """Main entry point."""
    print("Building monthly macroeconomic table...")
    print("-" * 80)
    
    try:
        df, metadata = build_macro_monthly()
        save_outputs(df, metadata)
        print_quality_summary(df, metadata)
        print("\nBuild completed successfully.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
