"""
World Bank Data Adapter.

Fetches macroeconomic indicators from the World Bank API (api.worldbank.org).
Uses the official REST API v2 with JSON format.

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin

import httpx

from app.core.schema import MacroObservation, Frequency
from app.core.series_registry import get_series, Source


# World Bank API Configuration
WB_API_BASE = "https://api.worldbank.org/v2/"
WB_DEFAULT_COUNTRY = "IND"
WB_PER_PAGE = 1000
WB_TIMEOUT = 30.0
WB_MAX_RETRIES = 3
WB_RETRY_BACKOFF = 2.0  # seconds


@dataclass
class WBRawResponse:
    """Container for raw World Bank API response with metadata."""
    indicator: str
    country: str
    data: list[dict]
    metadata: dict
    source_url: str
    retrieved_at: datetime
    raw_json: str


class WorldBankAdapter:
    """Adapter for fetching data from World Bank API."""
    
    def __init__(
        self,
        base_url: str = WB_API_BASE,
        timeout: float = WB_TIMEOUT,
        max_retries: int = WB_MAX_RETRIES,
        retry_backoff: float = WB_RETRY_BACKOFF,
        raw_data_dir: Optional[Path] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.raw_data_dir = raw_data_dir or Path("data/raw/world_bank")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=timeout)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _build_url(self, indicator: str, country: str = WB_DEFAULT_COUNTRY, 
                   start_year: Optional[int] = None, end_year: Optional[int] = None,
                   page: int = 1, per_page: int = WB_PER_PAGE) -> str:
        """Build World Bank API URL with parameters."""
        # Format: /v2/country/{country}/indicator/{indicator}
        path = f"country/{country}/indicator/{indicator}"
        url = urljoin(self.base_url, path)
        
        params = {
            "format": "json",
            "page": page,
            "per_page": per_page,
        }
        
        if start_year:
            params["date"] = f"{start_year}:{end_year or start_year}"
        
        return f"{url}?{urlencode(params)}"
    
    def _fetch_with_retry(self, url: str) -> httpx.Response:
        """Fetch URL with retry logic for transient failures."""
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
    
    def fetch_indicator(
        self,
        indicator: str,
        country: str = WB_DEFAULT_COUNTRY,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> WBRawResponse:
        """
        Fetch a single indicator for a country.
        
        Handles pagination automatically.
        
        Args:
            indicator: World Bank indicator code (e.g., "FP.CPI.TOTL.ZG")
            country: ISO country code (default "IND")
            start_year: Start year (optional)
            end_year: End year (optional)
        
        Returns:
            WBRawResponse with all pages of data
        
        Raises:
            httpx.HTTPError: On persistent failure
            ValueError: If response is empty or malformed
        """
        all_data = []
        page = 1
        total_pages = 1
        metadata = {}
        
        while page <= total_pages:
            url = self._build_url(indicator, country, start_year, end_year, page)
            response = self._fetch_with_retry(url)
            json_data = response.json()
            
            # World Bank API returns [metadata, data_array]
            if not isinstance(json_data, list) or len(json_data) < 2:
                raise ValueError(f"Unexpected response format: {json_data}")
            
            meta, data = json_data[0], json_data[1]
            
            if page == 1:
                metadata = meta
                total_pages = meta.get("pages", 1)
            
            if data:
                all_data.extend(data)
            
            page += 1
        
        if not all_data:
            raise ValueError(f"No data returned for indicator {indicator}, country {country}")
        
        source_url = self._build_url(indicator, country, start_year, end_year, 1)
        retrieved_at = datetime.utcnow()
        
        return WBRawResponse(
            indicator=indicator,
            country=country,
            data=all_data,
            metadata=metadata,
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_json=json.dumps(all_data, ensure_ascii=False),
        )
    
    def persist_raw(self, response: WBRawResponse) -> Path:
        """
        Persist raw response to disk.
        
        Never overwrites existing files - appends timestamp.
        """
        timestamp = response.retrieved_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{response.country}_{response.indicator}_{timestamp}.json"
        filepath = self.raw_data_dir / filename
        
        # Also save metadata separately
        meta_filename = f"{response.country}_{response.indicator}_{timestamp}_meta.json"
        meta_filepath = self.raw_data_dir / meta_filename
        
        # Save raw data
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "indicator": response.indicator,
                "country": response.country,
                "data": response.data,
                "metadata": response.metadata,
                "source_url": response.source_url,
                "retrieved_at": response.retrieved_at.isoformat(),
            }, f, ensure_ascii=False, indent=2)
        
        # Save metadata
        with open(meta_filepath, "w", encoding="utf-8") as f:
            json.dump(response.metadata, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def normalize_to_observations(
        self,
        response: WBRawResponse,
        canonical_series_id: str,
    ) -> list[MacroObservation]:
        """
        Normalize World Bank response to canonical MacroObservation schema.
        
        Args:
            response: Raw response from fetch_indicator
            canonical_series_id: Canonical series ID from registry
        
        Returns:
            List of MacroObservation objects
        """
        # Get registry entry for metadata
        registry_entry = get_series(canonical_series_id)
        
        observations = []
        
        for item in response.data:
            # World Bank returns: {"date": "2023", "value": 123.45, "country": {"id": "IND", "value": "India"}}
            date_str = item.get("date")
            value = item.get("value")
            
            if date_str is None or value is None:
                continue
            
            # Parse date - World Bank uses year format "2023" or "2023Q1"
            obs_date = self._parse_wb_date(date_str)
            if obs_date is None:
                continue
            
            # Determine frequency from date format
            freq = self._infer_frequency(date_str)
            
            # Get unit from registry or default
            unit = registry_entry.unit if registry_entry else "unknown"
            
            obs = MacroObservation(
                obs_date=obs_date,
                series_id=canonical_series_id,
                value=float(value),
                unit=unit,
                frequency=freq,
                source=Source.WORLD_BANK.value,
                source_url=response.source_url,
                release_date=None,  # WB doesn't provide release dates
                base_year=registry_entry.base_year if registry_entry else None,
                seasonal_adjustment=None,
                revision_tag=None,
                retrieved_at=response.retrieved_at,
            )
            observations.append(obs)
        
        return observations
    
    def _parse_wb_date(self, date_str: str) -> Optional[date]:
        """Parse World Bank date format (YYYY or YYYYQN)."""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Annual: "2023"
        if date_str.isdigit() and len(date_str) == 4:
            return date(int(date_str), 12, 31)
        
        # Quarterly: "2023Q1"
        if "Q" in date_str.upper():
            parts = date_str.upper().split("Q")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                year = int(parts[0])
                quarter = int(parts[1])
                month = quarter * 3
                return date(year, month, 31 if month in [3, 5, 7, 8, 10, 12] else 30)
        
        return None
    
    def _infer_frequency(self, date_str: str) -> Frequency:
        """Infer frequency from date string format."""
        if not date_str:
            return Frequency.ANNUAL
        
        date_str = str(date_str).strip().upper()
        if "Q" in date_str:
            return Frequency.QUARTERLY
        if date_str.isdigit() and len(date_str) == 4:
            return Frequency.ANNUAL
        return Frequency.ANNUAL
    
    def fetch_and_normalize(
        self,
        indicator: str,
        canonical_series_id: str,
        country: str = WB_DEFAULT_COUNTRY,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> list[MacroObservation]:
        """
        Convenience method: fetch, persist raw, and normalize in one call.
        """
        response = self.fetch_indicator(indicator, country, start_year, end_year)
        self.persist_raw(response)
        return self.normalize_to_observations(response, canonical_series_id)


def download_verified_indicator():
    """CLI/test function to download ONE verified India indicator."""
    # FP.CPI.TOTL.ZG = Inflation, consumer prices (annual %)
    # This is a well-documented WB indicator for India
    with WorldBankAdapter() as adapter:
        observations = adapter.fetch_and_normalize(
            indicator="FP.CPI.TOTL.ZG",
            canonical_series_id="cpi_headline",  # This maps to WB in registry alternatives
            country="IND",
            start_year=2000,
            end_year=2023,
        )
        
        print(f"Downloaded {len(observations)} observations for CPI (WB)")
        for obs in observations[:5]:
            print(f"  {obs.obs_date}: {obs.value}")
        
        return observations


if __name__ == "__main__":
    download_verified_indicator()