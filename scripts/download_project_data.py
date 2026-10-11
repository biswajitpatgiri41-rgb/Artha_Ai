"""Download the project data that is available through configured public APIs.

Run from the repository root with:
    python -m scripts.download_project_data

Raw provider responses remain in data/raw. Normalized canonical observations
and per-run status/provenance are written beneath data/interim and
data/manifests. Annual World Bank series are context only and must not be
interpolated into the monthly CPI training panel.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
load_dotenv(ROOT / ".env")

START_DATE = "2000-01-01"
START_YEAR = 2000

FRED_SERIES = [
    ("FEDFUNDS", "us_policy_rate"),
    ("CPIAUCSL", "us_cpi"),
    ("DEXINUS", "inr_usd"),
]

WORLD_BANK_SERIES = [
    ("FP.CPI.TOTL.ZG", "IND", "india_cpi_inflation_annual_wb"),
    ("NY.GDP.MKTP.KD.ZG", "IND", "india_gdp_growth_annual_wb"),
    ("NY.GDP.MKTP.KD.ZG", "WLD", "world_gdp_growth_annual_wb"),
]

NOT_YET_AUTOMATED = {
    "cpi_headline": "MoSPI CPI monthly index: provider download/API access not configured; required for the primary forecast target.",
    "food_inflation": "MoSPI food CPI monthly index: provider download/API access not configured; required for food inflation features.",
    "iip": "MoSPI IIP monthly index: provider download/API access not configured.",
    "repo_rate": "RBI repo rate history: RBI adapter/series mapping is still a placeholder.",
    "bank_credit": "RBI bank credit: RBI adapter/series mapping is still a placeholder.",
    "m3": "RBI M3: RBI adapter/series mapping is still a placeholder.",
    "rainfall_deviation": "IMD rainfall: IMD adapter/series mapping is still a placeholder.",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def absolute_path(path: Path | str) -> Path:
    result = Path(path)
    return result if result.is_absolute() else ROOT / result


def safe_error(exc: Exception) -> str:
    """Avoid accidentally putting credentials from request URLs in a report."""
    message = str(exc)
    message = re.sub(r"(?i)(api[_-]?key|token|access_token)=([^&\s]+)", r"\1=[REDACTED]", message)
    for key_name in ("FRED_API_KEY", "EIA_API_KEY"):
        secret = os.getenv(key_name)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return f"{type(exc).__name__}: {message[:500]}"


def serialize_observations(observations: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for obs in observations:
        freq = getattr(obs.frequency, "value", obs.frequency)
        rows.append({
            "obs_date": obs.obs_date.isoformat(),
            "series_id": obs.series_id,
            "value": obs.value,
            "unit": obs.unit,
            "frequency": freq,
            "source": obs.source,
            "source_url": obs.source_url,
            "release_date": obs.release_date.isoformat() if obs.release_date else None,
            "base_year": obs.base_year,
            "seasonal_adjustment": obs.seasonal_adjustment,
            "revision_tag": obs.revision_tag,
            "retrieved_at": obs.retrieved_at.isoformat() if obs.retrieved_at else None,
        })
    return rows


def write_normalized(series_id: str, provider_series_id: str, source: str, observations: list[Any]) -> Path:
    stamp = utc_now().strftime("%Y%m%d_%H%M%S_%f")
    path = ROOT / "data" / "interim" / f"{series_id}_normalized_{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = serialize_observations(observations)
    payload = {
        "canonical_series_id": series_id,
        "provider_series_id": provider_series_id,
        "source": source,
        "observation_count": len(rows),
        "observations": rows,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_manifest(series_id: str, provider_series_id: str, source: str,
                   observations: list[Any], raw_file: Path | None,
                   normalized_file: Path | None, source_url: str,
                   status: str = "SUCCESS", error: str | None = None) -> Path:
    dates = [obs.obs_date for obs in observations]
    stamp = utc_now().strftime("%Y%m%d_%H%M%S_%f")
    path = ROOT / "data" / "manifests" / f"manifest_{series_id}_{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "series_id": series_id,
        "provider_series_id": provider_series_id,
        "source": source,
        "source_url": source_url,
        "observation_count": len(observations),
        "min_date": min(dates).isoformat() if dates else None,
        "max_date": max(dates).isoformat() if dates else None,
        "frequency": getattr(observations[0].frequency, "value", observations[0].frequency) if observations else None,
        "unit": observations[0].unit if observations else None,
        "raw_file": str(raw_file.relative_to(ROOT)) if raw_file else None,
        "normalized_file": str(normalized_file.relative_to(ROOT)) if normalized_file else None,
        "status": status,
        "error": error,
        "created_at": utc_now().isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def fetch_fred(results: list[dict[str, Any]]) -> None:
    from app.tools.fred import FREDAdapter

    if not os.getenv("FRED_API_KEY") or os.getenv("FRED_API_KEY") == "your_fred_api_key_here":
        for provider_id, canonical_id in FRED_SERIES:
            results.append({"series_id": canonical_id, "source": "FRED", "status": "SKIPPED", "reason": "FRED_API_KEY is not configured"})
        return

    with FREDAdapter() as adapter:
        for provider_id, canonical_id in FRED_SERIES:
            try:
                observations = adapter.fetch_and_normalize(provider_id, canonical_id, observation_start=START_DATE)
                results.append({"series_id": canonical_id, "source": "FRED", "status": "SUCCESS", "observation_count": len(observations)})
                print(f"FRED {canonical_id}: {len(observations)} observations")
            except Exception as exc:
                results.append({"series_id": canonical_id, "source": "FRED", "status": "FAILED", "error": safe_error(exc)})
                print(f"FRED {canonical_id}: failed ({type(exc).__name__})")


def fetch_eia(results: list[dict[str, Any]]) -> None:
    from app.tools.eia import EIAAdapter

    if not os.getenv("EIA_API_KEY") or os.getenv("EIA_API_KEY") == "your_eia_api_key_here":
        results.append({"series_id": "brent_crude", "source": "EIA", "status": "SKIPPED", "reason": "EIA_API_KEY is not configured"})
        return

    try:
        with EIAAdapter() as adapter:
            observations, provider_manifest = adapter.fetch_and_normalize(
                provider_series_id="RBRTE", canonical_series_id="brent_crude",
                frequency="monthly", start="1987-05",
            )
            raw_file = absolute_path(provider_manifest.raw_file)
            normalized_file = write_normalized("brent_crude", "RBRTE", "EIA", observations)
            manifest_file = write_manifest(
                "brent_crude", "RBRTE", "EIA", observations, raw_file,
                normalized_file, "https://api.eia.gov/v2/petroleum/pri/spt/data/",
            )
            results.append({"series_id": "brent_crude", "source": "EIA", "status": "SUCCESS",
                            "observation_count": len(observations), "manifest": str(manifest_file.relative_to(ROOT))})
            print(f"EIA brent_crude: {len(observations)} observations")
    except Exception as exc:
        results.append({"series_id": "brent_crude", "source": "EIA", "status": "FAILED", "error": safe_error(exc)})
        print(f"EIA brent_crude: failed ({type(exc).__name__})")


def fetch_world_bank(results: list[dict[str, Any]]) -> None:
    from app.tools.world_bank import WorldBankAdapter

    with WorldBankAdapter() as adapter:
        for indicator, country, canonical_id in WORLD_BANK_SERIES:
            try:
                response = adapter.fetch_indicator(indicator, country, START_YEAR, utc_now().year)
                raw_file = absolute_path(adapter.persist_raw(response))
                observations = adapter.normalize_to_observations(response, canonical_id)
                normalized_file = write_normalized(canonical_id, indicator, "WORLD_BANK", observations)
                manifest_file = write_manifest(canonical_id, indicator, "WORLD_BANK", observations,
                                               raw_file, normalized_file, response.source_url)
                results.append({"series_id": canonical_id, "source": "WORLD_BANK", "status": "SUCCESS",
                                "observation_count": len(observations), "frequency": "annual",
                                "training_use": "context only; not monthly training data",
                                "manifest": str(manifest_file.relative_to(ROOT))})
                print(f"World Bank {canonical_id}: {len(observations)} annual observations (context only)")
            except Exception as exc:
                results.append({"series_id": canonical_id, "source": "WORLD_BANK", "status": "FAILED", "error": safe_error(exc)})
                print(f"World Bank {canonical_id}: failed ({type(exc).__name__})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", choices=("all", "fred", "eia", "world_bank"), default=["all"],
                        help="Sources to fetch (default: all)")
    args = parser.parse_args()
    sources = {"fred", "eia", "world_bank"} if "all" in args.sources else set(args.sources)

    results: list[dict[str, Any]] = []
    if "fred" in sources:
        fetch_fred(results)
    if "eia" in sources:
        fetch_eia(results)
    if "world_bank" in sources:
        fetch_world_bank(results)

    missing = [{"series_id": key, "status": "NOT_AUTOMATED", "reason": value}
               for key, value in NOT_YET_AUTOMATED.items()]
    run_id = utc_now().strftime("%Y%m%d_%H%M%S_%f")
    report_path = ROOT / "data" / "manifests" / f"download_run_{run_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id,
        "created_at": utc_now().isoformat(),
        "scope": "Configured API downloads; source list and unresolved monthly inputs are explicit.",
        "results": results,
        "required_but_not_automated": missing,
        "monthly_training_ready": False,
        "monthly_training_blockers": ["MoSPI CPI headline and food monthly indices are not present/configured."],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Run report: {report_path.relative_to(ROOT)}")
    successes = sum(item.get("status") == "SUCCESS" for item in results)
    failures = sum(item.get("status") == "FAILED" for item in results)
    print(f"Completed: {successes} successful series, {failures} failed series; {len(missing)} required inputs still need source configuration.")
    return 1 if failures and not successes else 0


if __name__ == "__main__":
    raise SystemExit(main())
