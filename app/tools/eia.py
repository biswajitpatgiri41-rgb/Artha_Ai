"""
EIA (U.S. Energy Information Administration) Adapter - API v2.

Fetches petroleum spot price data from the EIA API v2.
Requires EIA_API_KEY environment variable.

Official API Documentation: https://www.eia.gov/opendata/
Verified Route: https://api.eia.gov/v2/petroleum/pri/spt/data/
Series: RBRTE (Europe Brent Spot Price FOB)
Frequency: monthly
Unit: USD/barrel
"""

import hashlib
import json
import os
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.core.schema import MacroObservation, Frequency, SeasonalAdjustment
from app.core.series_registry import get_series, Source

# Load .env file
load_dotenv()

# EIA API v2 Configuration
EIA_API_BASE = "https://api.eia.gov/v2/"
EIA_PETROLEUM_PRI_SPT_ROUTE = "petroleum/pri/spt/data/"
EIA_TIMEOUT = 30.0
EIA_MAX_RETRIES = 3
EIA_RETRY_BACKOFF = 2.0  # seconds
DEFAULT_LENGTH = 5000

@dataclass
class EIARawResponse:
    """Container for raw EIA API v2 response with metadata."""
    provider_series_id: str
    data: list[dict]
    metadata: dict
    source_url: str
    retrieved_at: datetime
    raw_json: str
    frequency: str = "monthly"


@dataclass
class EIAProvenanceManifest:
    """Provenance manifest for EIA data ingestion."""
    series_id: str
    provider_series_id: str
    source: str
    api_version: str
    route: str
    retrieved_at: datetime
    observation_count: int
    min_date: Optional[date]
    max_date: Optional[date]
    frequency: str
    unit: str
    raw_file: str
    sha256_checksum: str
    status: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "series_id": self.series_id,
            "provider_series_id": self.provider_series_id,
            "source": self.source,
            "api_version": self.api_version,
            "route": self.route,
            "retrieved_at": self.retrieved_at.isoformat(),
            "observation_count": self.observation_count,
            "min_date": self.min_date.isoformat() if self.min_date else None,
            "max_date": self.max_date.isoformat() if self.max_date else None,
            "frequency": self.frequency,
            "unit": self.unit,
            "raw_file": self.raw_file,
            "sha256_checksum": self.sha256_checksum,
            "status": self.status,
            "warnings": self.warnings,
        }

class EIAAdapter:
    """Adapter for fetching data from EIA API v2."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = EIA_API_BASE,
        timeout: float = EIA_TIMEOUT,
        max_retries: int = EIA_MAX_RETRIES,
        retry_backoff: float = EIA_RETRY_BACKOFF,
        raw_data_dir: Optional[Path] = None,
    ):
        self.api_key = api_key or os.getenv("EIA_API_KEY")
        if not self.api_key:
            raise ValueError("EIA_API_KEY not provided and not found in environment")

        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.raw_data_dir = raw_data_dir or Path("data/raw/eia")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def _build_params(
        self,
        provider_series_id: str,
        frequency: str = "monthly",
        start: Optional[str] = None,
        end: Optional[str] = None,
        offset: int = 0,
        length: int = DEFAULT_LENGTH,
    ) -> dict:
        """Build EIA API v2 query parameters safely."""
        params = {
            "api_key": self.api_key,
            "frequency": frequency,
            "data[0]": "value",
            "facets[series][]": provider_series_id,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": length,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return params

    def _fetch_with_retry(self, url: str, params: dict) -> httpx.Response:
        """Fetch URL with retry logic for transient failures."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                raise

        raise last_error

    def fetch_series(
        self,
        provider_series_id: str,
        frequency: str = "monthly",
        start: Optional[str] = None,
        end: Optional[str] = None,
        offset: int = 0,
        length: int = DEFAULT_LENGTH,
    ) -> EIARawResponse:
        """
        Fetch a single series from EIA API v2.

        Args:
            provider_series_id: EIA series ID (e.g., "RBRTE")
            frequency: Data frequency ("monthly", "weekly", "daily", "annual")
            start: Start date in YYYY-MM or YYYY-MM-DD format
            end: End date in YYYY-MM or YYYY-MM-DD format
            offset: Pagination offset
            length: Number of records per request (max 5000)

        Returns:
            EIARawResponse containing the raw API response and metadata.
        """
        url = self.base_url + EIA_PETROLEUM_PRI_SPT_ROUTE
        params = self._build_params(
            provider_series_id=provider_series_id,
            frequency=frequency,
            start=start,
            end=end,
            offset=offset,
            length=length,
        )

        response = self._fetch_with_retry(url, params)
        response_json = response.json()
        retrieved_at = datetime.utcnow()

        # Keep provider credentials out of raw snapshots and provenance URLs.
        def redact_secrets(value):
            if isinstance(value, dict):
                return {
                    key: ("[REDACTED]" if key.lower() in {"api_key", "apikey", "token", "access_token"}
                          else redact_secrets(item))
                    for key, item in value.items()
                }
            if isinstance(value, list):
                return [redact_secrets(item) for item in value]
            return value

        parsed_url = urlsplit(str(response.url))
        safe_query = urlencode([
            (key, "[REDACTED]" if key.lower() in {"api_key", "apikey", "token", "access_token"} else value)
            for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
        ])
        source_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, safe_query, parsed_url.fragment))
        safe_response_json = redact_secrets(response_json)

        return EIARawResponse(
            provider_series_id=provider_series_id,
            data=response_json.get("response", {}).get("data", []),
            metadata=response_json.get("response", {}),
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_json=json.dumps(safe_response_json, ensure_ascii=False),
            frequency=frequency,
        )

    def persist_raw(self, response: EIARawResponse) -> Path:
        """
        Persist raw API response to disk.

        Never overwrites existing raw downloads - uses timestamp in filename.
        """
        timestamp = response.retrieved_at.strftime("%Y%m%d_%H%M%S")
        filename = f"eia_{response.provider_series_id}_{response.frequency}_{timestamp}.json"
        filepath = self.raw_data_dir / filename

        # Write raw JSON
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response.raw_json)

        return filepath

    def _parse_eia_period(self, period_str: str) -> Optional[date]:
        """
        Parse EIA v2 period format.

        Monthly: YYYY-MM
        Weekly: YYYY-MM-DD (or YYYY-Www)
        Daily: YYYY-MM-DD
        Annual: YYYY

        Returns the period end date (last day of month for monthly).
        """
        if not period_str:
            return None

        try:
            # Try YYYY-MM-DD first
            return datetime.strptime(period_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        try:
            # Try YYYY-MM (monthly) - return last day of month
            dt = datetime.strptime(period_str, "%Y-%m")
            # Get last day of month
            if dt.month == 12:
                next_month = dt.replace(year=dt.year + 1, month=1, day=1)
            else:
                next_month = dt.replace(month=dt.month + 1, day=1)
            return (next_month - timedelta(days=1)).date()
        except ValueError:
            pass

        try:
            # Try YYYY (annual) - return Dec 31
            year = int(period_str)
            return date(year, 12, 31)
        except ValueError:
            pass

        # Try YYYY-Www (weekly ISO week)
        if "-W" in period_str:
            try:
                year_str, week_str = period_str.split("-W")
                year = int(year_str)
                week = int(week_str)
                # Find the last day of the ISO week (Sunday)
                # ISO week 1 is the week with the first Thursday
                jan4 = date(year, 1, 4)
                week_start = jan4 - timedelta(days=jan4.weekday())
                target_week_start = week_start + timedelta(weeks=week - 1)
                week_end = target_week_start + timedelta(days=6)
                return week_end
            except (ValueError, IndexError):
                pass

        return None

    def normalize_to_observations(
        self,
        response: EIARawResponse,
        canonical_series_id: str,
    ) -> list[MacroObservation]:
        """
        Normalize EIA v2 raw response to MacroObservation list.

        Args:
            response: Raw EIA API response
            canonical_series_id: Canonical series ID from registry (e.g., "brent_crude")

        Returns:
            List of normalized MacroObservation objects.
        """
        registry_entry = get_series(canonical_series_id)
        observations = []

        # Validate response structure
        if not response.data:
            raise ValueError("Zero observations returned from EIA API")

        # Verify series matches
        for row in response.data:
            series_id = row.get("series")
            if series_id and series_id != response.provider_series_id:
                raise ValueError(f"Series mismatch: expected {response.provider_series_id}, got {series_id}")

        for row in response.data:
            period_str = row.get("period")
            value_str = row.get("value")
            series_id = row.get("series")

            if period_str is None or value_str is None:
                continue

            # Skip missing values
            if value_str in (".", "", None):
                continue

            # Parse date
            obs_date = self._parse_eia_period(period_str)
            if obs_date is None:
                continue

            # Validate numeric value
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                continue

            # Check for NaN/inf
            if value != value or value == float('inf') or value == float('-inf'):
                continue

            # Frequency from registry or response
            freq = registry_entry.frequency if registry_entry else Frequency.MONTHLY

            # Unit from registry or default
            unit = registry_entry.unit if registry_entry else "USD/barrel"

            obs = MacroObservation(
                obs_date=obs_date,
                series_id=canonical_series_id,
                value=value,
                unit=unit,
                frequency=freq,
                source=Source.EIA.value,
                source_url=response.source_url,
                release_date=None,  # EIA doesn't provide per-observation release dates
                base_year=registry_entry.base_year if registry_entry else None,
                seasonal_adjustment=SeasonalAdjustment.NSA,  # Spot prices are not seasonally adjusted
                revision_tag=None,
                retrieved_at=response.retrieved_at,
            )
            observations.append(obs)

        if not observations:
            raise ValueError("Zero valid observations after normalization")

        return observations

    def create_manifest(
        self,
        response: EIARawResponse,
        canonical_series_id: str,
        observations: list[MacroObservation],
        raw_file: Path,
    ) -> EIAProvenanceManifest:
        """Create provenance manifest for the ingestion."""
        dates = [obs.obs_date for obs in observations]
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None

        # Compute SHA-256 of raw file
        sha256_hash = hashlib.sha256()
        with open(raw_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        sha256_checksum = sha256_hash.hexdigest()

        return EIAProvenanceManifest(
            series_id=canonical_series_id,
            provider_series_id=response.provider_series_id,
            source=Source.EIA.value,
            api_version="v2",
            route=EIA_PETROLEUM_PRI_SPT_ROUTE,
            retrieved_at=response.retrieved_at,
            observation_count=len(observations),
            min_date=min_date,
            max_date=max_date,
            frequency=response.frequency,
            unit=observations[0].unit if observations else "USD/barrel",
            raw_file=str(raw_file),
            sha256_checksum=sha256_checksum,
            status="SUCCESS",
            warnings=[],
        )

    def fetch_and_normalize(
        self,
        provider_series_id: str,
        canonical_series_id: str,
        frequency: str = "monthly",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> tuple[list[MacroObservation], EIAProvenanceManifest]:
        """
        Convenience method: fetch, persist raw, normalize, and create manifest.

        Returns:
            Tuple of (observations, manifest)
        """
        response = self.fetch_series(
            provider_series_id=provider_series_id,
            frequency=frequency,
            start=start,
            end=end,
        )
        raw_file = self.persist_raw(response)
        observations = self.normalize_to_observations(response, canonical_series_id)
        manifest = self.create_manifest(response, canonical_series_id, observations, raw_file)
        return observations, manifest


def validate_ingestion(
    observations: list[MacroObservation],
    provider_series_id: str,
) -> list[str]:
    """
    Validate ingested data.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    if not observations:
        errors.append("Zero observations")
        return errors

    # Check all values are numeric
    for i, obs in enumerate(observations):
        if not isinstance(obs.value, (int, float)):
            errors.append(f"Observation {i}: value is not numeric: {obs.value}")
        elif obs.value != obs.value or obs.value == float('inf') or obs.value == float('-inf'):
            errors.append(f"Observation {i}: value is not finite: {obs.value}")

    # Check all periods parsed
    for i, obs in enumerate(observations):
        if obs.obs_date is None:
            errors.append(f"Observation {i}: period could not be parsed")

    return errors


def run_live_diagnostic() -> dict:
    """
    Run a live diagnostic ingestion of Brent crude monthly data.

    Returns summary dictionary.
    """
    summary = {
        "series": "RBRTE",
        "description": "Europe Brent Spot Price FOB",
        "frequency": "monthly",
        "unit": "USD/barrel",
        "observations": 0,
        "start": None,
        "end": None,
        "latest_value": None,
        "status": "FAILED",
        "error": None,
    }

    try:
        with EIAAdapter() as adapter:
            observations, manifest = adapter.fetch_and_normalize(
                provider_series_id="RBRTE",
                canonical_series_id="brent_crude",
                frequency="monthly",
            )

            # Validate
            errors = validate_ingestion(observations, "RBRTE")
            if errors:
                summary["status"] = "VALIDATION_FAILED"
                summary["error"] = "; ".join(errors)
                return summary

            # Save manifest
            manifest_dir = Path("data/manifests")
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_filename = f"manifest_brent_crude_{manifest.retrieved_at.strftime('%Y%m%d_%H%M%S')}.json"
            manifest_path = manifest_dir / manifest_filename
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.to_dict(), f, indent=2)

            # Save normalized observations to interim directory
            interim_dir = Path("data/interim")
            interim_dir.mkdir(parents=True, exist_ok=True)
            normalized_filename = f"brent_crude_normalized_{manifest.retrieved_at.strftime('%Y%m%d_%H%M%S')}.json"
            normalized_path = interim_dir / normalized_filename
            normalized_data = [obs.to_dict() for obs in observations]
            with open(normalized_path, "w", encoding="utf-8") as f:
                json.dump(normalized_data, f, indent=2)

            summary["observations"] = len(observations)
            summary["start"] = observations[0].obs_date.isoformat() if observations else None
            summary["end"] = observations[-1].obs_date.isoformat() if observations else None
            summary["latest_value"] = observations[-1].value if observations else None
            summary["status"] = "SUCCESS"
            summary["manifest_file"] = str(manifest_path)
            summary["normalized_file"] = str(normalized_path)
            summary["raw_file"] = manifest.raw_file
            summary["checksum"] = manifest.sha256_checksum

    except Exception as e:
        summary["status"] = "ERROR"
        summary["error"] = str(e)

    return summary


if __name__ == "__main__":
    # Live diagnostic callable: python -m app.tools.eia
    print("EIA Brent ingestion")
    print("Series: RBRTE")
    print("Description: Europe Brent Spot Price FOB")
    print("Frequency: monthly")
    print("Unit: USD/barrel")

    try:
        summary = run_live_diagnostic()

        if summary["status"] == "SUCCESS":
            print(f"Observations: {summary['observations']}")
            print(f"Start: {summary['start']}")
            print(f"End: {summary['end']}")
            print(f"Latest value: {summary['latest_value']}")
            print(f"Status: {summary['status']}")
            print(f"Raw File: {summary.get('raw_file', 'N/A')}")
            print(f"Normalized File: {summary.get('normalized_file', 'N/A')}")
            print(f"Manifest: {summary.get('manifest_file', 'N/A')}")
            print(f"Checksum: {summary.get('checksum', 'N/A')}")
        else:
            print(f"Observations: {summary['observations']}")
            print(f"Status: {summary['status']}")
            if summary.get("error"):
                print(f"Error: {summary['error']}")

    except ValueError as e:
        if "EIA_API_KEY" in str(e):
            print("Observations: 0")
            print("Status: SKIPPED (EIA_API_KEY not configured)")
        else:
            print(f"Observations: 0")
            print(f"Status: ERROR - {e}")
    except Exception as e:
        print(f"Observations: 0")
        print(f"Status: ERROR - {e}")
