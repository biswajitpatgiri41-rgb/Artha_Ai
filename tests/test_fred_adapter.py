"""
Tests for FRED Adapter with mocked responses.
"""

import json
import os
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.tools.fred import FREDAdapter
from app.core.schema import MacroObservation, Frequency
from app.core.series_registry import get_series


class TestFREDAdapter:
    """Test FRED Adapter with mocked HTTP responses."""

    @pytest.fixture
    def mock_fred_response_fedfunds(self):
        return {
            "realtime_start": "2024-01-01",
            "realtime_end": "2024-01-01",
            "observations": [
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-01-01", "value": "4.33"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-02-01", "value": "4.57"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-03-01", "value": "4.57"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-04-01", "value": "4.83"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-05-01", "value": "5.08"},
            ]
        }

    @pytest.fixture
    def mock_fred_response_cpi(self):
        return {
            "realtime_start": "2024-01-01",
            "realtime_end": "2024-01-01",
            "observations": [
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-01-01", "value": "299.170"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-02-01", "value": "300.840"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-03-01", "value": "301.836"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-04-01", "value": "303.363"},
                {"realtime_start": "2024-01-01", "realtime_end": "2024-01-01", "date": "2023-05-01", "value": "304.127"},
            ]
        }

    @pytest.fixture
    def mock_fred_series_metadata(self):
        return {
            "seriess": [
                {
                    "id": "FEDFUNDS",
                    "seasonal_adjustment": "Not Seasonally Adjusted",
                }
            ]
        }

    @pytest.fixture
    def mock_fred_series_metadata_cpi(self):
        return {
            "seriess": [
                {
                    "id": "CPIAUCSL",
                    "seasonal_adjustment": "Seasonally Adjusted",
                }
            ]
        }

    def test_adapter_init_with_key(self):
        adapter = FREDAdapter(api_key="test_key_123")
        assert adapter.api_key == "test_key_123"
        assert adapter.key_configured is True
        adapter.client.close()

    def test_adapter_init_without_key(self, monkeypatch):
        # Remove FRED_API_KEY from environment to test "no key" scenario
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        adapter = FREDAdapter(api_key=None)
        assert adapter.api_key is None
        assert adapter.key_configured is False
        adapter.client.close()

    def test_adapter_init_with_placeholder_key(self):
        adapter = FREDAdapter(api_key="your_fred_api_key_here")
        assert adapter.key_configured is False
        adapter.client.close()

    @patch("app.tools.fred.httpx.Client")
    def test_fetch_series_fedfunds(self, mock_client_class, mock_fred_response_fedfunds, mock_fred_series_metadata):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response_obs = Mock()
        mock_response_obs.json.return_value = mock_fred_response_fedfunds
        mock_response_obs.text = json.dumps(mock_fred_response_fedfunds)
        mock_response_obs.raise_for_status = Mock()
        mock_response_meta = Mock()
        mock_response_meta.json.return_value = mock_fred_series_metadata
        mock_response_meta.raise_for_status = Mock()
        mock_client.get.side_effect = [mock_response_obs, mock_response_meta]
        adapter = FREDAdapter(api_key="test_key")
        response = adapter.fetch_series("FEDFUNDS", observation_start="2023-01-01")
        assert response.series_id == "FEDFUNDS"
        assert len(response.data) == 5
        assert response.data[0]["date"] == "2023-01-01"
        assert response.data[0]["value"] == "4.33"
        assert response.metadata["seasonal_adjustment"] == "Not Seasonally Adjusted"
        adapter.client.close()

    @patch("app.tools.fred.httpx.Client")
    def test_fetch_series_cpi(self, mock_client_class, mock_fred_response_cpi, mock_fred_series_metadata_cpi):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response_obs = Mock()
        mock_response_obs.json.return_value = mock_fred_response_cpi
        mock_response_obs.text = json.dumps(mock_fred_response_cpi)
        mock_response_obs.raise_for_status = Mock()
        mock_response_meta = Mock()
        mock_response_meta.json.return_value = mock_fred_series_metadata_cpi
        mock_response_meta.raise_for_status = Mock()
        mock_client.get.side_effect = [mock_response_obs, mock_response_meta]
        adapter = FREDAdapter(api_key="test_key")
        response = adapter.fetch_series("CPIAUCSL", observation_start="2023-01-01")
        assert response.series_id == "CPIAUCSL"
        assert len(response.data) == 5
        assert response.data[0]["value"] == "299.170"
        assert response.metadata["seasonal_adjustment"] == "Seasonally Adjusted"
        adapter.client.close()