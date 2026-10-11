"""
Tests for canonical schema and normalization utilities.
"""

import pytest
from datetime import date, datetime
from app.core.schema import (
    MacroObservation,
    Frequency,
    SeasonalAdjustment,
    parse_date_flexible,
    parse_frequency,
    parse_seasonal_adjustment,
    validate_observation,
    detect_duplicates,
    detect_missing_values,
    sort_observations,
    check_date_ordering,
)


class TestMacroObservation:
    """Tests for the MacroObservation dataclass."""
    
    def test_create_basic_observation(self):
        """Test creating a basic observation."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        assert obs.obs_date == date(2024, 1, 15)
        assert obs.series_id == "test_series"
        assert obs.value == 100.5
        assert obs.unit == "index"
        assert obs.frequency == Frequency.MONTHLY
        assert obs.source == "TEST"
        assert obs.hash is not None
        assert len(obs.hash) == 16
    
    def test_observation_to_dict(self):
        """Test serialization to dictionary."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        d = obs.to_dict()
        
        assert d["obs_date"] == "2024-01-15"
        assert d["series_id"] == "test_series"
        assert d["value"] == 100.5
        assert d["unit"] == "index"
        assert d["frequency"] == "M"
        assert d["source"] == "TEST"
        assert d["hash"] == obs.hash
    
    def test_observation_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "obs_date": "2024-01-15",
            "series_id": "test_series",
            "value": 100.5,
            "unit": "index",
            "frequency": "M",
            "source": "TEST",
            "source_url": "http://example.com",
            "release_date": "2024-02-01",
            "base_year": "2012",
            "seasonal_adjustment": "SA",
            "revision_tag": "preliminary",
            "retrieved_at": "2024-02-15T10:00:00",
            "hash": "abc123",
        }
        
        obs = MacroObservation.from_dict(data)
        
        assert obs.obs_date == date(2024, 1, 15)
        assert obs.series_id == "test_series"
        assert obs.value == 100.5
        assert obs.release_date == date(2024, 2, 1)
        assert obs.base_year == "2012"
        assert obs.seasonal_adjustment == SeasonalAdjustment.SA
        assert obs.revision_tag == "preliminary"
        assert obs.retrieved_at == datetime(2024, 2, 15, 10, 0, 0)
    
    def test_hash_consistency(self):
        """Test that same content produces same hash."""
        obs1 = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        obs2 = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        assert obs1.hash == obs2.hash
    
    def test_hash_different_for_different_values(self):
        """Test that different values produce different hashes."""
        obs1 = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        obs2 = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=101.5,  # Different value
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        assert obs1.hash != obs2.hash


class TestParseDateFlexible:
    """Tests for parse_date_flexible function."""
    
    def test_iso_date(self):
        assert parse_date_flexible("2024-01-15") == date(2024, 1, 15)
    
    def test_iso_month(self):
        assert parse_date_flexible("2024-01") == date(2024, 1, 1)
    
    def test_iso_year(self):
        assert parse_date_flexible("2024") == date(2024, 1, 1)
    
    def test_quarter_format(self):
        assert parse_date_flexible("2024-Q1") == date(2024, 3, 31)
        assert parse_date_flexible("2024-Q2") == date(2024, 6, 30)
        assert parse_date_flexible("2024-Q3") == date(2024, 9, 30)
        assert parse_date_flexible("2024-Q4") == date(2024, 12, 31)
    
    def test_dd_mm_yyyy(self):
        assert parse_date_flexible("15/01/2024") == date(2024, 1, 15)
    
    def test_mm_dd_yyyy(self):
        assert parse_date_flexible("01/15/2024") == date(2024, 1, 15)
    
    def test_compact_date(self):
        assert parse_date_flexible("20240115") == date(2024, 1, 15)
    
    def test_month_name(self):
        assert parse_date_flexible("Jan 2024") == date(2024, 1, 1)
        assert parse_date_flexible("January 2024") == date(2024, 1, 1)
    
    def test_invalid_date(self):
        assert parse_date_flexible("invalid") is None
        assert parse_date_flexible("") is None
        assert parse_date_flexible(None) is None


class TestParseFrequency:
    """Tests for parse_frequency function."""
    
    def test_annual(self):
        assert parse_frequency("A") == Frequency.ANNUAL
        assert parse_frequency("ANNUAL") == Frequency.ANNUAL
        assert parse_frequency("YEARLY") == Frequency.ANNUAL
    
    def test_quarterly(self):
        assert parse_frequency("Q") == Frequency.QUARTERLY
        assert parse_frequency("QUARTERLY") == Frequency.QUARTERLY
    
    def test_monthly(self):
        assert parse_frequency("M") == Frequency.MONTHLY
        assert parse_frequency("MONTHLY") == Frequency.MONTHLY
    
    def test_weekly(self):
        assert parse_frequency("W") == Frequency.WEEKLY
        assert parse_frequency("WEEKLY") == Frequency.WEEKLY
    
    def test_daily(self):
        assert parse_frequency("D") == Frequency.DAILY
        assert parse_frequency("DAILY") == Frequency.DAILY
    
    def test_fortnightly(self):
        assert parse_frequency("F") == Frequency.FORTNIGHTLY
        assert parse_frequency("FORTNIGHTLY") == Frequency.FORTNIGHTLY
        assert parse_frequency("BIWEEKLY") == Frequency.FORTNIGHTLY
    
    def test_irregular(self):
        assert parse_frequency("I") == Frequency.IRREGULAR
        assert parse_frequency("IRREGULAR") == Frequency.IRREGULAR
        assert parse_frequency("UNKNOWN") == Frequency.IRREGULAR


class TestParseSeasonalAdjustment:
    """Tests for parse_seasonal_adjustment function."""
    
    def test_sa(self):
        assert parse_seasonal_adjustment("SA") == SeasonalAdjustment.SA
        assert parse_seasonal_adjustment("SEASONALLY ADJUSTED") == SeasonalAdjustment.SA
        assert parse_seasonal_adjustment("SEASADJ") == SeasonalAdjustment.SA
    
    def test_nsa(self):
        assert parse_seasonal_adjustment("NSA") == SeasonalAdjustment.NSA
        assert parse_seasonal_adjustment("NOT SEASONALLY ADJUSTED") == SeasonalAdjustment.NSA
        assert parse_seasonal_adjustment("NOTSEASADJ") == SeasonalAdjustment.NSA
        assert parse_seasonal_adjustment("UNADJUSTED") == SeasonalAdjustment.NSA
    
    def test_unknown(self):
        assert parse_seasonal_adjustment(None) == SeasonalAdjustment.UNKNOWN
        assert parse_seasonal_adjustment("") == SeasonalAdjustment.UNKNOWN
        assert parse_seasonal_adjustment("INVALID") == SeasonalAdjustment.UNKNOWN