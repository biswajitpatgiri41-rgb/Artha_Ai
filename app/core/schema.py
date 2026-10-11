"""
Canonical Macroeconomic Observation Schema.

This module defines the normalized data structure for all macroeconomic
observations, regardless of source. Every observation from any provider
must be normalized to this schema before being stored in the processed layer.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
from enum import Enum
import hashlib


class Frequency(str, Enum):
    """Observation frequency."""
    ANNUAL = "A"
    QUARTERLY = "Q"
    MONTHLY = "M"
    WEEKLY = "W"
    DAILY = "D"
    FORTNIGHTLY = "F"
    IRREGULAR = "I"


class SeasonalAdjustment(str, Enum):
    """Seasonal adjustment status."""
    SA = "SA"
    NSA = "NSA"
    UNKNOWN = "UNKNOWN"


class Source(str, Enum):
    """Data source identifiers."""
    RBI = "RBI"
    MOSPI = "MOSPI"
    WORLD_BANK = "WORLD_BANK"
    FRED = "FRED"
    IMF = "IMF"
    EIA = "EIA"
    IMD = "IMD"
    OECD = "OECD"


@dataclass
class MacroObservation:
    """Canonical macroeconomic observation."""
    obs_date: Optional[date] = None
    series_id: str = ""
    value: Optional[float] = None
    unit: str = ""
    frequency: Optional[Frequency] = None
    source: str = ""
    source_url: Optional[str] = None
    release_date: Optional[date] = None
    base_year: Optional[str] = None
    seasonal_adjustment: SeasonalAdjustment = SeasonalAdjustment.UNKNOWN
    revision_tag: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    hash: str = field(init=False, default="")

    def __post_init__(self):
        if self.obs_date is not None:
            content = f"{self.obs_date.isoformat()}|{self.series_id}|{self.value}|{self.unit}|{self.frequency.value if self.frequency else ''}|{self.source}"
            self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        else:
            self.hash = ""

    def to_dict(self) -> dict:
        return {
            "obs_date": self.obs_date.isoformat(),
            "series_id": self.series_id,
            "value": self.value,
            "unit": self.unit,
            "frequency": self.frequency.value,
            "source": self.source,
            "source_url": self.source_url,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "base_year": self.base_year,
            "seasonal_adjustment": self.seasonal_adjustment.value,
            "revision_tag": self.revision_tag,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MacroObservation":
        obs_date = date.fromisoformat(data["obs_date"])
        frequency = Frequency(data["frequency"])
        seasonal_adjustment = SeasonalAdjustment(data.get("seasonal_adjustment", "UNKNOWN"))
        release_date = None
        if data.get("release_date"):
            release_date = date.fromisoformat(data["release_date"])
        retrieved_at = None
        if data.get("retrieved_at"):
            retrieved_at = datetime.fromisoformat(data["retrieved_at"])
        obs = cls(
            obs_date=obs_date,
            series_id=data["series_id"],
            value=data["value"],
            unit=data["unit"],
            frequency=frequency,
            source=data["source"],
            source_url=data.get("source_url"),
            release_date=release_date,
            base_year=data.get("base_year"),
            seasonal_adjustment=seasonal_adjustment,
            revision_tag=data.get("revision_tag"),
            retrieved_at=retrieved_at,
        )
        if "hash" in data:
            obs.hash = data["hash"]
        return obs


def parse_date_flexible(date_str: Optional[str]) -> Optional[date]:
    """Parse date string in various formats."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try ISO format YYYY-MM-DD
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        pass

    # Try YYYY-MM (monthly) - return first day of month
    try:
        dt = datetime.strptime(date_str, "%Y-%m")
        return dt.date()
    except ValueError:
        pass

    # Try YYYY (annual) - return Jan 1
    try:
        year = int(date_str)
        return date(year, 1, 1)
    except ValueError:
        pass

    # Try YYYY-QN (quarterly) - return quarter end
    if "-Q" in date_str.upper():
        try:
            year_str, quarter_str = date_str.upper().split("-Q")
            year = int(year_str)
            quarter = int(quarter_str)
            if quarter == 1:
                return date(year, 3, 31)
            elif quarter == 2:
                return date(year, 6, 30)
            elif quarter == 3:
                return date(year, 9, 30)
            elif quarter == 4:
                return date(year, 12, 31)
        except (ValueError, IndexError):
            pass

    # Try DD/MM/YYYY
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        pass

    # Try MM/DD/YYYY
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except ValueError:
        pass

    # Try YYYYMMDD compact
    try:
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        pass

    # Try month name formats
    for fmt in ["%b %Y", "%B %Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass

    return None


def parse_frequency(freq_str: Optional[str]) -> Frequency:
    """Parse frequency string to Frequency enum."""
    if not freq_str:
        return Frequency.IRREGULAR

    freq_str = freq_str.upper().strip()

    mapping = {
        "A": Frequency.ANNUAL,
        "ANNUAL": Frequency.ANNUAL,
        "YEARLY": Frequency.ANNUAL,
        "Y": Frequency.ANNUAL,
        "Q": Frequency.QUARTERLY,
        "QUARTERLY": Frequency.QUARTERLY,
        "M": Frequency.MONTHLY,
        "MONTHLY": Frequency.MONTHLY,
        "W": Frequency.WEEKLY,
        "WEEKLY": Frequency.WEEKLY,
        "D": Frequency.DAILY,
        "DAILY": Frequency.DAILY,
        "F": Frequency.FORTNIGHTLY,
        "FORTNIGHTLY": Frequency.FORTNIGHTLY,
        "BIWEEKLY": Frequency.FORTNIGHTLY,
        "I": Frequency.IRREGULAR,
        "IRREGULAR": Frequency.IRREGULAR,
        "UNKNOWN": Frequency.IRREGULAR,
    }

    return mapping.get(freq_str, Frequency.IRREGULAR)


def parse_seasonal_adjustment(sa_str: Optional[str]) -> SeasonalAdjustment:
    """Parse seasonal adjustment string to SeasonalAdjustment enum."""
    if not sa_str:
        return SeasonalAdjustment.UNKNOWN

    sa_str = sa_str.upper().strip()

    if sa_str in ("SA", "SEASONALLY ADJUSTED", "SEASADJ", "ADJUSTED"):
        return SeasonalAdjustment.SA
    elif sa_str in ("NSA", "NOT SEASONALLY ADJUSTED", "NOTSEASADJ", "UNADJUSTED", "NOT ADJUSTED"):
        return SeasonalAdjustment.NSA

    return SeasonalAdjustment.UNKNOWN


def validate_observation(obs: MacroObservation, registry: Optional[dict] = None) -> list[str]:
    """Validate a single observation. Returns list of error messages (empty if valid)."""
    errors = []

    if obs.obs_date is None:
        errors.append("obs_date is required")

    if not obs.series_id:
        errors.append("series_id is required")

    if obs.value is None:
        errors.append("value is required")
    elif obs.value != obs.value or obs.value == float('inf') or obs.value == float('-inf'):
        errors.append("value must be finite")

    if not obs.unit:
        errors.append("unit is required")

    if obs.frequency is None:
        errors.append("frequency is required")

    if not obs.source:
        errors.append("source is required")

    # Registry mismatch checks
    if registry and obs.series_id in registry:
        reg_entry = registry[obs.series_id]
        if hasattr(reg_entry, 'unit') and reg_entry.unit != obs.unit:
            errors.append(f"unit mismatch with registry: expected {reg_entry.unit}, got {obs.unit}")
        if hasattr(reg_entry, 'frequency') and reg_entry.frequency != obs.frequency:
            errors.append(f"frequency mismatch with registry: expected {reg_entry.frequency}, got {obs.frequency}")

    return errors


def detect_duplicates(observations: list[MacroObservation]) -> list[tuple[int, int]]:
    """Detect duplicate observations (same series_id and obs_date). Returns list of index pairs (i, j) where i < j."""
    seen = {}
    duplicates = []

    for i, obs in enumerate(observations):
        key = (obs.series_id, obs.obs_date)
        if key in seen:
            duplicates.append((seen[key], i))
        else:
            seen[key] = i

    return duplicates


def detect_missing_values(observations: list[MacroObservation]) -> list[tuple[str, date]]:
    """Detect observations with missing (None or NaN) values. Returns list of (series_id, obs_date)."""
    missing = []

    for obs in observations:
        if obs.value is None or (isinstance(obs.value, float) and obs.value != obs.value):
            missing.append((obs.series_id, obs.obs_date))

    return missing


def sort_observations(observations: list[MacroObservation]) -> list[MacroObservation]:
    """Sort observations by series_id then obs_date."""
    return sorted(observations, key=lambda x: (x.series_id, x.obs_date))


def check_date_ordering(observations: list[MacroObservation]) -> list[str]:
    """Check that observations for each series are in strictly increasing date order in the original list. Returns warnings."""
    warnings = []

    # Group by series_id preserving original order
    by_series = {}
    for i, obs in enumerate(observations):
        if obs.series_id not in by_series:
            by_series[obs.series_id] = []
        by_series[obs.series_id].append((i, obs))

    for series_id, series_obs in by_series.items():
        for i in range(1, len(series_obs)):
            _, prev_obs = series_obs[i-1]
            _, curr_obs = series_obs[i]
            if curr_obs.obs_date is not None and prev_obs.obs_date is not None:
                if curr_obs.obs_date <= prev_obs.obs_date:
                    warnings.append(
                        f"Series {series_id}: observation at {curr_obs.obs_date} "
                        f"is not strictly after previous {prev_obs.obs_date}"
                    )

    return warnings