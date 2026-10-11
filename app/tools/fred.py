"""
FRED (Federal Reserve Economic Data) Adapter.

Fetches US macroeconomic data from the FRED API.
Requires FRED_API_KEY environment variable.

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin

import httpx

from app.core.schema import MacroObservation, Frequency
from app.core.series_registry import get_series, Source


# FRED API Configuration
FRED_API_BASE = "https://api.stlouisfed.org/fred/"
FRED_TIMEOUT = 30.0
FRED_MAX_RETRIES = 3
FRED_RETRY_BACKOFF = 2.0  # seconds


@dataclass
class FREDRawResponse:
    """Container for raw FRED API response with metadata."""
    series_id: str
    data: list[dict]
    metadata: dict
    source_url: str
    retrieved_at: datetime
    raw_json: str


class FREDAdapter:
    """Adapter for fetching data from FRED API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = FRED_API_BASE,
        timeout: float = FRED_TIMEOUT,
        max_retries: int = FRED_MAX_RETRIES,
        retry_backoff: float = FRED_RETRY_BACKOFF,
        raw_data_dir: Optional[Path] = None,
    ):
        # Load from environment if not provided (supports dotenv)
        # Only fall back to env if api_key is not explicitly provided (i.e., not None)
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("FRED_API_KEY")
        # Allow instantiation without valid key for diagnostic purposes
        # Actual API calls will validate the key
        self.key_configured = bool(self.api_key and self.api_key != "your_fred_api_key_here")
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.raw_data_dir = raw_data_dir or Path("data/raw/fred")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure interim and manifest directories exist
        Path("data/interim").mkdir(parents=True, exist_ok=True)
        Path("data/manifests").mkdir(parents=True, exist_ok=True)
        
        self.client = httpx.Client(timeout=timeout)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _build_url(self, endpoint: str, **params) -> str:
        """Build FRED API URL with parameters."""
        url = urljoin(self.base_url, endpoint)
        params["api_key"] = self.api_key
        params["file_type"] = "json"
        return f"{url}?{urlencode(params)}"
    
    def _fetch_with_retry(self, url: str) -> httpx.Response:
        """Fetch URL with retry logic for transient failures."""
        if not self.key_configured:
            raise ValueError("FRED_API_KEY not configured")
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url)
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
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        units: Optional[str] = None,
    ) -> FREDRawResponse:
        """
        Fetch a single series from FRED.
        
        Args:
            series_id: FRED series ID (e.g., "FEDFUNDS", "CPIAUCSL")
            observation_start: Start date in YYYY-MM-DD format (optional)
            observation_end: End date in YYYY-MM-DD format (optional)
            units: Data transformation (e.g., "lin", "chg", "pch", "pc1")
        
        Returns:
            FREDRawResponse with observations and metadata
        
        Raises:
            httpx.HTTPError: On persistent failure
            ValueError: If response is empty or malformed
        """
        # Fetch observations
        obs_params = {"series_id": series_id}
        if observation_start:
            obs_params["observation_start"] = observation_start
        if observation_end:
            obs_params["observation_end"] = observation_end
        if units:
            obs_params["units"] = units
        
        obs_url = self._build_url("series/observations", **obs_params)
        obs_response = self._fetch_with_retry(obs_url)
        obs_json = obs_response.json()
        
        # Fetch series metadata
        meta_url = self._build_url("series", series_id=series_id)
        meta_response = self._fetch_with_retry(meta_url)
        meta_json = meta_response.json()
        
        observations = obs_json.get("observations", [])
        series_meta = meta_json.get("seriess", [{}])[0]
        
        if not observations:
            raise ValueError(f"No observations returned for series {series_id}")
        
        source_url = f"https://fred.stlouisfed.org/series/{series_id}"
        retrieved_at = datetime.utcnow()
        
        return FREDRawResponse(
            series_id=series_id,
            data=observations,
            metadata=series_meta,
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_json=json.dumps(observations, ensure_ascii=False),
        )
    
    def persist_raw(self, response: FREDRawResponse) -> Path:
        """
        Persist raw response to disk.
        
        Never overwrites existing files - appends timestamp.
        """
        timestamp = response.retrieved_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{response.series_id}_{timestamp}.json"
        filepath = self.raw_data_dir / filename
        
        # Also save metadata separately
        meta_filename = f"{response.series_id}_{timestamp}_meta.json"
        meta_filepath = self.raw_data_dir / meta_filename
        
        # Save raw data
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "series_id": response.series_id,
                "data": response.data,
                "metadata": response.metadata,
                "source_url": response.source_url,
                "retrieved_at": response.retrieved_at.isoformat(),
            }, f, ensure_ascii=False, indent=2)
        
        # Save metadata
        with open(meta_filepath, "w", encoding="utf-8") as f:
            json.dump(response.metadata, f, ensure_ascii=False, indent=2)
        
        return filepath

    def persist_normalized(
        self,
        observations: list[MacroObservation],
        canonical_series_id: str,
        provider_series_id: str,
    ) -> Path:
        """
        Persist normalized observations to disk.
        
        Never overwrites existing files - appends timestamp.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{canonical_series_id}_normalized_{timestamp}.json"
        filepath = Path("data/interim") / filename

        data = {
            "canonical_series_id": canonical_series_id,
            "provider_series_id": provider_series_id,
            "observation_count": len(observations),
            "observations": [
                {
                    "obs_date": obs.obs_date.isoformat(),
                    "series_id": obs.series_id,
                    "value": obs.value,
                    "unit": obs.unit,
                    "frequency": obs.frequency.value if hasattr(obs.frequency, 'value') else str(obs.frequency),
                    "source": obs.source,
                    "base_year": obs.base_year,
                    "seasonal_adjustment": obs.seasonal_adjustment,
                    "revision_tag": obs.revision_tag,
                    "retrieved_at": obs.retrieved_at.isoformat() if obs.retrieved_at else None,
                }
                for obs in observations
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def create_manifest(
        self,
        raw_file: Path,
        normalized_file: Path,
        canonical_series_id: str,
        provider_series_id: str,
        observations: list[MacroObservation],
        registry_entry,
        raw_json: str,
    ) -> Path:
        """
        Create a manifest file documenting the data fetch and normalization.
        
        Never overwrites existing files - appends timestamp.
        """
        if not observations:
            raise ValueError("No observations to create manifest for")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"manifest_{canonical_series_id}_{timestamp}.json"
        filepath = Path("data/manifests") / filename

        # Calculate checksum of raw JSON
        checksum = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

        # Get date range
        dates = [obs.obs_date for obs in observations]
        min_date = min(dates).isoformat()
        max_date = max(dates).isoformat()

        # Get frequency from first observation
        freq = observations[0].frequency
        if hasattr(freq, 'value'):
            freq = freq.value

        # Get seasonal adjustment from first observation
        sa = observations[0].seasonal_adjustment

        # Get unit from first observation
        unit = observations[0].unit

        manifest = {
            "series_id": canonical_series_id,
            "provider_series_id": provider_series_id,
            "source": "FRED",
            "source_url": f"https://fred.stlouisfed.org/series/{provider_series_id}",
            "observation_count": len(observations),
            "min_date": min_date,
            "max_date": max_date,
            "frequency": freq,
            "unit": unit,
            "seasonal_adjustment": sa,
            "base_year": registry_entry.base_year if registry_entry else None,
            "status": "SUCCESS",
            "checksum_sha256": checksum,
            "raw_file": str(raw_file),
            "normalized_file": str(normalized_file),
            "created_at": datetime.utcnow().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return filepath

    def normalize_to_observations(
        self,
        response: FREDRawResponse,
        canonical_series_id: str,
    ) -> list[MacroObservation]:
        """
        Normalize FRED response to canonical MacroObservation schema.
        
        Args:
            response: Raw response from fetch_series
            canonical_series_id: Canonical series ID from registry
        
        Returns:
            List of MacroObservation objects
        """
        # Get registry entry for metadata
        registry_entry = get_series(canonical_series_id)
        
        # Get seasonal adjustment from FRED metadata
        seasonal_adjustment = "unknown"
        if response.metadata and "seasonal_adjustment" in response.metadata:
            sa = response.metadata["seasonal_adjustment"]
            if sa == "Seasonally Adjusted":
                seasonal_adjustment = "seasonally_adjusted"
            elif sa == "Not Seasonally Adjusted":
                seasonal_adjustment = "not_seasonally_adjusted"
        
        observations = []
        
        for item in response.data:
            # FRED returns: {"date": "2024-01-01", "value": "5.25", "realtime_start": "...", "realtime_end": "..."}
            date_str = item.get("date")
            value_str = item.get("value")
            
            if date_str is None or value_str is None:
                continue
            
            # Skip missing values (FRED uses ".")
            if value_str == ".":
                continue
            
            # Parse date - FRED uses YYYY-MM-DD
            obs_date = self._parse_fred_date(date_str)
            if obs_date is None:
                continue
            
            # Determine frequency from registry or metadata
            freq = registry_entry.frequency if registry_entry else Frequency.MONTHLY
            
            # Get unit from registry or default
            unit = registry_entry.unit if registry_entry else "unknown"
            
            try:
                value = float(value_str)
            except ValueError:
                continue
            
            obs = MacroObservation(
                obs_date=obs_date,
                series_id=canonical_series_id,
                value=value,
                unit=unit,
                frequency=freq,
                source=Source.FRED.value,
                source_url=response.source_url,
                release_date=None,  # FRED observations don't have release dates per observation
                base_year=registry_entry.base_year if registry_entry else None,
                seasonal_adjustment=seasonal_adjustment,
                revision_tag=None,
                retrieved_at=response.retrieved_at,
            )
            observations.append(obs)
        
        # Sort chronologically
        observations.sort(key=lambda x: x.obs_date)
        
        return observations
    
    def _parse_fred_date(self, date_str: str) -> Optional[date]:
        """Parse FRED date format (YYYY-MM-DD)."""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None
    
    def fetch_and_normalize(
        self,
        series_id: str,
        canonical_series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        units: Optional[str] = None,
    ) -> list[MacroObservation]:
        """
        Convenience method: fetch, persist raw, normalize, persist normalized, create manifest.
        
        Returns:
            List of MacroObservation objects
        """
        response = self.fetch_series(series_id, observation_start, observation_end, units)
        
        # Persist raw response
        raw_file = self.persist_raw(response)
        
        # Normalize
        observations = self.normalize_to_observations(response, canonical_series_id)
        
        # Persist normalized
        normalized_file = self.persist_normalized(observations, canonical_series_id, series_id)
        
        # Create manifest
        registry_entry = get_series(canonical_series_id)
        self.create_manifest(
            raw_file=raw_file,
            normalized_file=normalized_file,
            canonical_series_id=canonical_series_id,
            provider_series_id=series_id,
            observations=observations,
            registry_entry=registry_entry,
            raw_json=response.raw_json,
        )
        
        return observations
    
    def live_diagnostic(self, series_id: str = "FEDFUNDS") -> dict:
        """
        Run a live diagnostic fetch for a series.
        
        Returns diagnostic information without full persistence.
        """
        if not self.api_key or self.api_key == "your_fred_api_key_here":
            return {
                "status": "FRED_API_KEY: NOT CONFIGURED",
                "series_id": series_id,
                "error": "FRED_API_KEY not configured in environment",
            }
        
        try:
            response = self.fetch_series(series_id, observation_start="2020-01-01")
            obs_count = len(response.data)
            dates = [item.get("date") for item in response.data if item.get("value") != "."]
            valid_dates = [d for d in dates if d]
            
            return {
                "status": "SUCCESS",
                "series_id": series_id,
                "http_status": 200,
                "total_observations": obs_count,
                "valid_observations": len(valid_dates),
                "earliest_date": min(valid_dates) if valid_dates else None,
                "latest_date": max(valid_dates) if valid_dates else None,
                "metadata_keys": list(response.metadata.keys()),
                "sample_observations": response.data[:3] if response.data else [],
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "series_id": series_id,
                "error": str(e),
            }


def download_verified_series():
    """CLI/test function to download verified FRED series."""
    # Check if API key is configured
    api_key = os.getenv("FRED_API_KEY")
    if not api_key or api_key == "your_fred_api_key_here":
        print("FRED_API_KEY: NOT CONFIGURED")
        print("Please set FRED_API_KEY in .env file")
        return None, None
    
    with FREDAdapter() as adapter:
        # Download US Federal Funds Rate
        print("Downloading US Federal Funds Rate (FEDFUNDS)...")
        fedfunds = adapter.fetch_and_normalize(
            series_id="FEDFUNDS",
            canonical_series_id="us_policy_rate",
            observation_start="2000-01-01",
        )
        print(f"Downloaded {len(fedfunds)} observations")
        for obs in fedfunds[:5]:
            print(f"  {obs.obs_date}: {obs.value}")
        
        # Download US CPI
        print("\nDownloading US CPI (CPIAUCSL)...")
        cpi = adapter.fetch_and_normalize(
            series_id="CPIAUCSL",
            canonical_series_id="us_cpi",
            observation_start="2000-01-01",
        )
        print(f"Downloaded {len(cpi)} observations")
        for obs in cpi[:5]:
            print(f"  {obs.obs_date}: {obs.value}")
        
        return fedfunds, cpi


if __name__ == "__main__":
    download_verified_series()