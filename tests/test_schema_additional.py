"""
Additional tests for canonical schema and normalization utilities.
"""

import pytest
from datetime import date, datetime
from app.core.schema import (
    MacroObservation,
    Frequency,
    SeasonalAdjustment,
    validate_observation,
    detect_duplicates,
    detect_missing_values,
    sort_observations,
    check_date_ordering,
)


class TestValidateObservation:
    """Tests for validate_observation function."""
    
    def test_valid_observation(self):
        """Test validation of valid observation."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        errors = validate_observation(obs)
        assert errors == []
    
    def test_missing_obs_date(self):
        """Test validation fails for missing obs_date."""
        obs = MacroObservation(
            obs_date=None,  # type: ignore
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        errors = validate_observation(obs)
        assert "obs_date is required" in errors
    
    def test_missing_series_id(self):
        """Test validation fails for missing series_id."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="",
            value=100.5,
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        errors = validate_observation(obs)
        assert "series_id is required" in errors
    
    def test_missing_value(self):
        """Test validation fails for missing value."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=None,  # type: ignore
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        errors = validate_observation(obs)
        assert "value is required" in errors
    
    def test_nan_value(self):
        """Test validation fails for NaN value."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=float('nan'),
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        errors = validate_observation(obs)
        assert "value must be finite" in errors
    
    def test_infinite_value(self):
        """Test validation fails for infinite value."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=float('inf'),
            unit="index",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        errors = validate_observation(obs)
        assert "value must be finite" in errors
    
    def test_registry_mismatch_unit(self):
        """Test validation detects unit mismatch with registry."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="wrong_unit",
            frequency=Frequency.MONTHLY,
            source="TEST",
        )
        
        registry = {
            "test_series": type('obj', (object,), {
                'unit': 'index',
                'frequency': Frequency.MONTHLY
            })()
        }
        
        errors = validate_observation(obs, registry)
        assert any("unit mismatch" in e for e in errors)
    
    def test_registry_mismatch_frequency(self):
        """Test validation detects frequency mismatch with registry."""
        obs = MacroObservation(
            obs_date=date(2024, 1, 15),
            series_id="test_series",
            value=100.5,
            unit="index",
            frequency=Frequency.ANNUAL,
            source="TEST",
        )
        
        registry = {
            "test_series": type('obj', (object,), {
                'unit': 'index',
                'frequency': Frequency.MONTHLY
            })()
        }
        
        errors = validate_observation(obs, registry)
        assert any("frequency mismatch" in e for e in errors)
class TestDetectDuplicates:
    """Tests for detect_duplicates function."""
    
    def test_no_duplicates(self):
        """Test no duplicates detected."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 2, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs3 = MacroObservation(obs_date=date(2024, 1, 1), series_id="B", value=3, unit="u", frequency=Frequency.MONTHLY, source="S")
        
        duplicates = detect_duplicates([obs1, obs2, obs3])
        assert duplicates == []
    
    def test_duplicates_detected(self):
        """Test duplicates detected."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 2, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs3 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=3, unit="u", frequency=Frequency.MONTHLY, source="S")  # Duplicate
        
        duplicates = detect_duplicates([obs1, obs2, obs3])
        assert duplicates == [(0, 2)]


class TestDetectMissingValues:
    """Tests for detect_missing_values function."""
    
    def test_no_missing(self):
        """Test no missing values."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 2, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        
        missing = detect_missing_values([obs1, obs2])
        assert missing == []
    
    def test_none_value(self):
        """Test None value detected."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=None, unit="u", frequency=Frequency.MONTHLY, source="S")  # type: ignore
        
        missing = detect_missing_values([obs1])
        assert missing == [("A", date(2024, 1, 1))]
    
    def test_nan_value(self):
        """Test NaN value detected."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=float('nan'), unit="u", frequency=Frequency.MONTHLY, source="S")
        
        missing = detect_missing_values([obs1])
        assert missing == [("A", date(2024, 1, 1))]


class TestSortObservations:
    """Tests for sort_observations function."""
    
    def test_sorts_by_series_then_date(self):
        """Test sorting by series_id then obs_date."""
        obs1 = MacroObservation(obs_date=date(2024, 3, 1), series_id="B", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs3 = MacroObservation(obs_date=date(2024, 2, 1), series_id="A", value=3, unit="u", frequency=Frequency.MONTHLY, source="S")
        
        sorted_obs = sort_observations([obs1, obs2, obs3])
        
        assert sorted_obs[0].series_id == "A"
        assert sorted_obs[0].obs_date == date(2024, 1, 1)
        assert sorted_obs[1].series_id == "A"
        assert sorted_obs[1].obs_date == date(2024, 2, 1)
        assert sorted_obs[2].series_id == "B"
        assert sorted_obs[2].obs_date == date(2024, 3, 1)


class TestCheckDateOrdering:
    """Tests for check_date_ordering function."""
    
    def test_valid_ordering(self):
        """Test no warnings for valid ordering."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 2, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs3 = MacroObservation(obs_date=date(2024, 3, 1), series_id="A", value=3, unit="u", frequency=Frequency.MONTHLY, source="S")
        
        warnings = check_date_ordering([obs1, obs2, obs3])
        assert warnings == []
    
    def test_invalid_ordering(self):
        """Test warning for invalid ordering."""
        obs1 = MacroObservation(obs_date=date(2024, 3, 1), series_id="A", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs3 = MacroObservation(obs_date=date(2024, 2, 1), series_id="A", value=3, unit="u", frequency=Frequency.MONTHLY, source="S")
        
        warnings = check_date_ordering([obs1, obs2, obs3])
        assert len(warnings) == 1  # Only 3->1 is out of order; 1->2 is in order
        assert "not strictly after" in warnings[0]
    
    def test_same_date_warning(self):
        """Test warning for same date (not strictly increasing)."""
        obs1 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=1, unit="u", frequency=Frequency.MONTHLY, source="S")
        obs2 = MacroObservation(obs_date=date(2024, 1, 1), series_id="A", value=2, unit="u", frequency=Frequency.MONTHLY, source="S")
        
        warnings = check_date_ordering([obs1, obs2])
        assert len(warnings) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])