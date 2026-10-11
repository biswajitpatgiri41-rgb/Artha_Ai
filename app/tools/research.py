"""Deterministic research calculations used by the HTTP API.

The helpers deliberately use only observations already present in the project.
They never manufacture missing official data or treat mock UI values as data.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.series_registry import SERIES_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
INTERIM = ROOT / "data" / "interim"


@dataclass(frozen=True)
class Observation:
    date: str
    value: float
    series_id: str
    source: str
    unit: str
    source_url: str | None = None
    release_date: str | None = None
    retrieved_at: str | None = None
    base_year: str | None = None


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def load_series(series_id: str) -> list[Observation]:
    """Load a series from canonical processed tables or normalized snapshots."""
    entry = SERIES_REGISTRY.get(series_id)
    if not entry:
        return []
    result: dict[str, Observation] = {}

    for filename in ("macro_monthly.csv", "cpi_features.csv"):
        path = PROCESSED / filename
        if not path.exists():
            continue
        column = {
            "cpi_headline": "cpi_index", "food_inflation": "food_index",
            "brent_crude": "brent_price", "inr_usd": "inr_usd",
            "repo_rate": "repo_rate", "iip": "iip_yoy", "cpi_yoy": "cpi_yoy",
        }.get(series_id, series_id)
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    value = _number(row.get(column))
                    date = row.get("date")
                    if value is not None and date:
                        result[date[:10]] = Observation(
                            date[:10], value, series_id,
                            row.get(f"{column}_source") or entry.preferred_source.value,
                            entry.unit, entry.source_url, row.get(f"{column}_release_date"),
                            row.get(f"{column}_retrieved_at"), entry.base_year,
                        )
        except (OSError, csv.Error):
            continue

    snapshots = sorted(INTERIM.glob(f"{series_id}_normalized_*.json"), key=lambda item: item.stat().st_mtime)
    for path in snapshots:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            observations = payload.get("observations", []) if isinstance(payload, dict) else payload
            if isinstance(payload, dict) and payload.get("mode") == "replace":
                result.clear()
            for item in observations:
                date = str(item.get("obs_date", ""))[:10]
                value = _number(item.get("value"))
                if date and value is not None:
                    # Later snapshots are the explicit correction/update for
                    # a date; upload mode=upsert relies on this precedence.
                    result[date] = Observation(
                        date, value, series_id,
                        str(item.get("source", entry.preferred_source.value)),
                        str(item.get("unit", entry.unit)), item.get("source_url", entry.source_url),
                        item.get("release_date"), item.get("retrieved_at"),
                        item.get("base_year", entry.base_year),
                    )
        except (OSError, ValueError, TypeError):
            continue
    if series_id == "cpi_yoy":
        headline = load_series("cpi_headline")
        by_month = {item.date[:7]: item for item in headline}
        for current in headline:
            year, month = map(int, current.date[:7].split("-"))
            previous_key = f"{year - 1:04d}-{month:02d}"
            previous = by_month.get(previous_key)
            if previous and previous.value > 0:
                result[current.date] = Observation(
                    current.date, (current.value / previous.value - 1) * 100,
                    "cpi_yoy", current.source, "percent", current.source_url,
                    current.release_date, current.retrieved_at, current.base_year,
                )
        # Use the checked-in MoSPI 2024-base target only when no project data
        # or normalized snapshots supplied this series. Do not mix CPI bases.
        if not result:
            try:
                from app.models.final_package import load_packaged_cpi_target

                for item in load_packaged_cpi_target():
                    result[item["date"]] = Observation(
                        item["date"], item["value"], "cpi_yoy",
                        entry.preferred_source.value, entry.unit,
                        entry.source_url, base_year=item["base_year"],
                    )
            except FileNotFoundError:
                pass
    return [result[key] for key in sorted(result)]


def catalog() -> list[dict[str, Any]]:
    rows = []
    for series_id, entry in SERIES_REGISTRY.items():
        observations = load_series(series_id)
        rows.append({
            "id": series_id, "description": entry.description,
            "source": entry.preferred_source.value, "provider_series_id": entry.provider_series_id,
            "frequency": entry.frequency.value, "unit": entry.unit, "base_year": entry.base_year,
            "enabled": entry.enabled, "available": bool(observations),
            "observation_count": len(observations),
            "latest": asdict(observations[-1]) if observations else None,
        })
    return rows


def seasonal_naive(series_id: str = "cpi_yoy", horizon: int = 6) -> dict[str, Any]:
    if not 1 <= horizon <= 24:
        raise ValueError("horizon must be between 1 and 24 months")
    observations = load_series(series_id)
    if not observations:
        raise LookupError(f"No observations are available for {series_id}")
    values = [item.value for item in observations]
    # Repeat the latest annual seasonal pattern where possible; otherwise use
    # a transparent last-observation baseline.
    forecasts = []
    for step in range(1, horizon + 1):
        value = values[-12 + ((step - 1) % 12)] if len(values) >= 12 else values[-1]
        forecasts.append({"step": step, "value": value})
    return {
        "series_id": series_id, "model": "seasonal_naive",
        "status": "computed", "mode": "observed_data",
        "origin": observations[-1].date, "horizon_months": horizon,
        "forecasts": forecasts,
        "source_observations": len(observations),
        "source": observations[-1].source, "unit": observations[-1].unit,
        "warnings": (["Fewer than 12 observations; forecast repeats the latest value."]
                     if len(values) < 12 else ["Baseline benchmark only; not an official or causal forecast."]),
    }


def rolling_backtest(series_id: str = "cpi_yoy", horizon: int = 1,
                     min_train: int = 24) -> dict[str, Any]:
    if not 1 <= horizon <= 12 or min_train < 2:
        raise ValueError("horizon must be 1–12 months and min_train at least 2")
    observations = load_series(series_id)
    if len(observations) < min_train + horizon:
        raise LookupError(f"Backtest needs at least {min_train + horizon} observations; found {len(observations)}")
    actual: list[float] = []
    predicted: list[float] = []
    for origin in range(min_train, len(observations) - horizon + 1):
        train = [item.value for item in observations[:origin]]
        target_index = origin + horizon - 1
        predicted.append(train[target_index - 12] if target_index >= 12 and target_index - 12 < len(train) else train[-1])
        actual.append(observations[target_index].value)
    errors = [a - p for a, p in zip(actual, predicted)]
    return {
        "series_id": series_id, "model": "seasonal_naive", "horizon_months": horizon,
        "origins": len(errors), "mae": sum(abs(e) for e in errors) / len(errors),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "bias": sum(errors) / len(errors),
        "coverage_80": None, "coverage_95": None,
        "interval_note": "Intervals are not estimated by this benchmark.",
        "data_start": observations[0].date, "data_end": observations[-1].date,
        "warnings": ["Expanding-window benchmark; results depend on available revisions and history."],
    }


def simulate_scenario(base_inflation: float, oil_change_pct: float,
                      inr_change_pct: float, food_shock_pp: float,
                      repo_change_bp: float, horizon: int) -> dict[str, Any]:
    """Return the project's original illustrative linear sensitivity estimate."""
    inputs = [base_inflation, oil_change_pct, inr_change_pct, food_shock_pp, repo_change_bp]
    if not all(math.isfinite(value) for value in inputs):
        raise ValueError("scenario values must be finite")
    if not 1 <= horizon <= 24 or abs(oil_change_pct) > 200 or abs(inr_change_pct) > 50 or abs(food_shock_pp) > 20 or abs(repo_change_bp) > 500:
        raise ValueError("scenario inputs exceed supported bounds")
    oil_effect = 0.025 * oil_change_pct
    fx_effect = -0.08 * inr_change_pct
    food_effect = food_shock_pp
    policy_effect = -0.0015 * repo_change_bp * min(horizon, 12) / 6
    delta = oil_effect + fx_effect + food_effect + policy_effect
    return {
        "mode": "illustrative_sensitivity", "baseline_inflation": base_inflation,
        "scenario_inflation": base_inflation + delta, "change_pp": delta,
        "horizon_months": horizon,
        "effects_pp": {"oil": oil_effect, "inr": fx_effect, "food": food_effect, "repo": policy_effect},
        "assumptions": {"oil_pp_per_pct": 0.025, "inr_pp_per_pct": 0.08,
                        "food_pp_per_pp": 1.0, "repo_pp_per_bp_6m": -0.0015},
        "warnings": ["Illustrative linear sensitivities for a student prototype; coefficients are not estimated from Indian data and must not be interpreted causally."],
    }
