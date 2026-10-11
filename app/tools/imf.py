"""
IMF (International Monetary Fund) Data Adapter.

Fetches macroeconomic data from the IMF SDMX API.
Supports IFS (International Financial Statistics) and other datasets.

API Documentation: https://data.imf.org/
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


# IMF API Configuration
IMF_API_BASE = "https://dataservices.imf.org/REST/SDMX_JSON.svc/"
IMF_TIMEOUT = 60.0  # IMF can be slow
IMF_MAX_RETRIES = 3
IMF_RETRY_BACKOFF = 5.0  # seconds


@dataclass
class IMFFlowResponse:
    """Container for raw IMF API response with metadata."""
    dataset: str
    dimension: str
    data: list[dict]
    metadata: dict
    source_url: str
    retrieved_at: datetime
    raw_json: str


class IMFAdapter:
    """Adapter for fetching data from IMF SDMX API."""
    
    def __init__(
        self,
        base_url: str = IMF_API_BASE,
        timeout: float = IMF_TIMEOUT,
        max_retries: int = IMF_MAX_RETRIES,
        retry_backoff: float = IMF_RETRY_BACKOFF,
        raw_data_dir: Optional[Path] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.raw_data_dir = raw_data_dir or Path("data/raw/imf")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=timeout)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _build_url(self, dataset: str, dimension: str, **params) -> str:
        """Build IMF SDMX API URL."""
        # Format: /CompactData/{dataset}/{dimension}
        path = f"CompactData/{dataset}/{dimension}"
        url = urljoin(self.base_url, path)
        if params:
            return f"{url}?{urlencode(params)}"
        return url
    
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
    
    def fetch_compact_data(
        self,
        dataset: str,
        dimension: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ) -> IMFFlowResponse:
        """
        Fetch compact data from IMF SDMX API.
        
        Args:
            dataset: IMF dataset code (e.g., "IFS" for International Financial Statistics)
            dimension: Dimension filter (e.g., "M.IND.FP_CPI_IX" for India CPI monthly)
            start_period: Start period (e.g., "2000-01")
            end_period: End period (e.g., "2024-12")
        
        Returns:
            IMFFlowResponse with observations
        """
        params = {}
        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period
        
        url = self._build_url(dataset, dimension, **params)
        response = self._fetch_with_retry(url)
        json_data = response.json()
        
        # IMF SDMX-JSON structure
        compact_data = json_data.get("CompactData", {})
        dataset_data = compact_data.get("DataSet", {})
        series = dataset_data.get("Series", [])
        
        # Handle both single series and list of series
        if isinstance(series, dict):
            series = [series]
        
        all_obs = []
        for s in series:
            obs_list = s.get("Obs", [])
            if isinstance(obs_list, dict):
                obs_list = [obs_list]
            
            # Add series attributes to each observation
            for obs in obs_list:
                obs["@SERIES_ATTRS"] = {k: v for k, v in s.items() if k != "Obs"}
            
            all_obs.extend(obs_list)
        
        if not all_obs:
            raise ValueError(f"No observations returned for {dataset}/{dimension}")
        
        source_url = f"https://data.imf.org/?sk={dataset}"
        retrieved_at = datetime.utcnow()
        
        return IMFFlowResponse(
            dataset=dataset,
            dimension=dimension,
            data=all_obs,
            metadata=dataset_data,
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_json=json.dumps(all_obs, ensure_ascii=False),
        )
    
    def persist_raw(self, response: IMFFlowResponse) -> Path:
        """
        Persist raw response to disk.
        """
        timestamp = response.retrieved_at.strftime("%Y%m%d_%H%M%S")
        # Sanitize dimension for filename
        safe_dim = response.dimension.replace(".", "_").replace(",", "_")
        filename = f"{response.dataset}_{safe_dim}_{timestamp}.json"
        filepath = self.raw_data_dir / filename
        
        meta_filename = f"{response.dataset}_{safe_dim}_{timestamp}_meta.json"
        meta_filepath = self.raw_data_dir / meta_filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "dataset": response.dataset,
                "dimension": response.dimension,
                "data": response.data,
                "metadata": response.metadata,
                "source_url": response.source_url,
                "retrieved_at": response.retrieved_at.isoformat(),
            }, f, ensure_ascii=False, indent=2)
        
        with open(meta_filepath, "w", encoding="utf-8") as f:
            json.dump(response.metadata, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def normalize_to_observations(
        self,
        response: IMFFlowResponse,
        canonical_series_id: str,
    ) -> list[MacroObservation]:
        """
        Normalize IMF response to canonical MacroObservation schema.
        """
        registry_entry = get_series(canonical_series_id)
        
        observations = []
        
        for item in response.data:
            time_period = item.get("@TIME_PERIOD")
            value_str = item.get("@OBS_VALUE")
            
            if time_period is None or value_str is None:
                continue
            
            obs_date = self._parse_imf_period(time_period)
            if obs_date is None:
                continue
            
            freq = self._infer_frequency(time_period)
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
                source=Source.IMF.value,
                source_url=response.source_url,
                release_date=None,
                base_year=registry_entry.base_year if registry_entry else None,
                seasonal_adjustment=None,
                revision_tag=None,
                retrieved_at=response.retrieved_at,
            )
            observations.append(obs)
        
        return observations
    
    def _parse_imf_period(self, period_str: str) -> Optional[date]:
        """Parse IMF period format (YYYY-MM, YYYY-QN, YYYY)."""
        if not period_str:
            return None
        
        period_str = str(period_str).strip()
        
        # Monthly: "2024-01"
        if "-" in period_str and len(period_str) >= 7:
            try:
                year, month = period_str.split("-")[:2]
                return date(int(year), int(month), 28)  # End of month approx
            except ValueError:
                pass
        
        # Quarterly: "2024-Q1"
        if "-Q" in period_str.upper():
            parts = period_str.upper().split("-Q")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                year = int(parts[0])
                quarter = int(parts[1])
                month = quarter * 3
                return date(year, month, 31 if month in [3, 5, 7, 8, 10, 12] else 30)
        
        # Annual: "2024"
        if period_str.isdigit() and len(period_str) == 4:
            return date(int(period_str), 12, 31)
        
        return None
    
    def _infer_frequency(self, period_str: str) -> Frequency:
        """Infer frequency from period string format."""
        if not period_str:
            return Frequency.ANNUAL
        
        period_str = str(period_str).strip().upper()
        if "-Q" in period_str:
            return Frequency.QUARTERLY
        if "-" in period_str and len(period_str) >= 7:
            return Frequency.MONTHLY
        if period_str.isdigit() and len(period_str) == 4:
            return Frequency.ANNUAL
        return Frequency.ANNUAL
    
    def fetch_and_normalize(
        self,
        dataset: str,
        dimension: str,
        canonical_series_id: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ) -> list[MacroObservation]:
        """
        Convenience method: fetch, persist raw, and normalize in one call.
        """
        response = self.fetch_compact_data(dataset, dimension, start_period, end_period)
        self.persist_raw(response)
        return self.normalize_to_observations(response, canonical_series_id)


def download_verified_series():
    """CLI/test function to download verified IMF series for India."""
    with IMFAdapter() as adapter:
        # IFS dataset, India CPI (monthly)
        # M.IND.FP_CPI_IX = Monthly, India, Consumer Price Index
        print("Downloading India CPI from IMF IFS...")
        cpi = adapter.fetch_and_normalize(
            dataset="IFS",
            dimension="M.IND.FP_CPI_IX",
            canonical_series_id="cpi_headline",
            start_period="2000-01",
            end_period="2024-12",
        )
        print(f"Downloaded {len(cpi)} observations")
        for obs in cpi[:5]:
            print(f"  {obs.obs_date}: {obs.value}")
        
        return cpi


if __name__ == "__main__":
    download_verified_series()