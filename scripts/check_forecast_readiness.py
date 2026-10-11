#!/usr/bin/env python
"""
Forecast Data Readiness Checker.

Determines whether we have enough REAL data to train the CPI forecasting pipeline.
Checks all required MVP feature series and reports their status.

Run with: python -m scripts.check_forecast_readiness
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.core.series_registry import get_series, Source, SERIES_REGISTRY, Frequency
from app.config.forecasting import SERIES_MAPPING, MIN_OBSERVATIONS_TRAINING

# MVP feature series to check (feature name -> registry canonical_id)
MVP_FEATURE_SERIES = [
    ("cpi_yoy", "cpi_headline"),
    ("food_inflation_yoy", "food_inflation"),
    ("brent_crude", "brent_crude"),
    ("inr_usd", "inr_usd"),
    ("repo_rate", "repo_rate"),
    ("iip_yoy", "iip"),
]

# Optional series for reference
OPTIONAL_SERIES = [
    ("us_policy_rate", "us_policy_rate"),
    ("us_cpi_index", "us_cpi"),
]


def find_latest_normalized_file(canonical_id: str) -> Optional[Path]:
    """Find the latest normalized data file for a canonical series ID."""
    interim_dir = Path("data/interim")
    if not interim_dir.exists():
        return None

    pattern = f"{canonical_id}_normalized_*.json"
    files = list(interim_dir.glob(pattern))
    if not files:
        return None

    # Sort by modification time, newest first
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0]


def load_normalized_observations(filepath: Path) -> list[dict]:
    """Load normalized observations from a JSON file.
    
    Handles both formats:
    - EIA: direct array of observations
    - FRED: wrapper object with "observations" key
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # FRED format: {"canonical_series_id": "...", "observations": [...]}
    if isinstance(data, dict) and "observations" in data:
        return data["observations"]
    
    # EIA format: direct array [...]
    if isinstance(data, list):
        return data
    
    # Fallback: return empty list
    return []


def analyze_series(feature_name: str, canonical_id: str) -> dict:
    """Analyze a single series and return readiness metrics."""
    registry_entry = get_series(canonical_id)

    if registry_entry is None:
        return {
            "feature_name": feature_name,
            "canonical_id": canonical_id,
            "source": "UNKNOWN",
            "status": "NOT_REGISTERED",
            "frequency": None,
            "observation_count": 0,
            "earliest_date": None,
            "latest_date": None,
            "missing_months": 0,
            "unit": None,
            "enabled": False,
            "provider_series_id": None,
        }

    # Find latest normalized file
    latest_file = find_latest_normalized_file(canonical_id)

    if latest_file is None:
        return {
            "feature_name": feature_name,
            "canonical_id": canonical_id,
            "source": registry_entry.preferred_source.value,
            "status": "MISSING",
            "frequency": registry_entry.frequency.value,
            "observation_count": 0,
            "earliest_date": None,
            "latest_date": None,
            "missing_months": 0,
            "unit": registry_entry.unit,
            "enabled": registry_entry.enabled,
            "provider_series_id": registry_entry.provider_series_id,
        }

    # Load and analyze observations
    observations = load_normalized_observations(latest_file)

    if not observations:
        return {
            "feature_name": feature_name,
            "canonical_id": canonical_id,
            "source": registry_entry.preferred_source.value,
            "status": "EMPTY",
            "frequency": registry_entry.frequency.value,
            "observation_count": 0,
            "earliest_date": None,
            "latest_date": None,
            "missing_months": 0,
            "unit": registry_entry.unit,
            "enabled": registry_entry.enabled,
            "provider_series_id": registry_entry.provider_series_id,
        }

    # Parse dates and count
    dates = []
    for obs in observations:
        try:
            d = datetime.strptime(obs["obs_date"], "%Y-%m-%d").date()
            dates.append(d)
        except (KeyError, ValueError):
            continue

    if not dates:
        return {
            "feature_name": feature_name,
            "canonical_id": canonical_id,
            "source": registry_entry.preferred_source.value,
            "status": "INVALID",
            "frequency": registry_entry.frequency.value,
            "observation_count": 0,
            "earliest_date": None,
            "latest_date": None,
            "missing_months": 0,
            "unit": registry_entry.unit,
            "enabled": registry_entry.enabled,
            "provider_series_id": registry_entry.provider_series_id,
        }

    obs_count = len(dates)
    earliest = min(dates)
    latest = max(dates)

    # Calculate missing months (for monthly frequency)
    missing_months = 0
    if registry_entry.frequency == Frequency.MONTHLY and len(dates) > 1:
        expected_months = (latest.year - earliest.year) * 12 + (latest.month - earliest.month) + 1
        missing_months = max(0, expected_months - obs_count)

    # Determine status
    if not registry_entry.enabled:
        status = "DISABLED"
    elif obs_count < MIN_OBSERVATIONS_TRAINING:
        status = "INSUFFICIENT"
    else:
        status = "READY"

    return {
        "feature_name": feature_name,
        "canonical_id": canonical_id,
        "source": registry_entry.preferred_source.value,
        "status": status,
        "frequency": registry_entry.frequency.value,
        "observation_count": obs_count,
        "earliest_date": earliest.isoformat(),
        "latest_date": latest.isoformat(),
        "missing_months": missing_months,
        "unit": registry_entry.unit,
        "enabled": registry_entry.enabled,
        "provider_series_id": registry_entry.provider_series_id,
    }


def format_status_line(result: dict, is_optional: bool = False) -> str:
    """Format a single result line for output."""
    feature = result["feature_name"]
    status = result["status"]
    source = result["source"]
    obs_count = result["observation_count"]

    prefix = "Optional: " if is_optional else ""

    if status == "READY":
        return f"{prefix}{feature:<25} {status:<12} {source}"
    elif status in ("MISSING", "NOT_REGISTERED", "DISABLED", "EMPTY", "INVALID"):
        return f"{prefix}{feature:<25} {status}"
    else:  # INSUFFICIENT
        return f"{prefix}{feature:<25} {status:<12} {source} {obs_count} obs (need {MIN_OBSERVATIONS_TRAINING}+)"


def main():
    """Main entry point for readiness check."""
    print("CPI Forecast Readiness", flush=True)
    print("=" * 60, flush=True)

    # Check MVP series
    mvp_results = []
    for feature_name, canonical_id in MVP_FEATURE_SERIES:
        result = analyze_series(feature_name, canonical_id)
        mvp_results.append(result)
        print(format_status_line(result), flush=True)

    print(flush=True)

    # Check optional series
    optional_results = []
    for feature_name, canonical_id in OPTIONAL_SERIES:
        result = analyze_series(feature_name, canonical_id)
        optional_results.append(result)
        print(format_status_line(result, is_optional=True), flush=True)

    print(flush=True)

    # Overall assessment
    ready_count = sum(1 for r in mvp_results if r["status"] == "READY")
    total_count = len(mvp_results)

    if ready_count == total_count:
        overall = "READY"
    else:
        overall = "NOT READY"

    print(f"Overall: {overall}", flush=True)


if __name__ == "__main__":
    main()