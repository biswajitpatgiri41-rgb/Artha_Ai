"""Core configuration, LLM client, series registry, and schema."""

from .series_registry import (
    SeriesRegistryEntry,
    Frequency,
    Source,
    SERIES_REGISTRY,
    get_series,
    get_enabled_series,
    get_series_by_source,
    list_all_series,
    register,
)

from .schema import (
    MacroObservation,
    Frequency as SchemaFrequency,
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

__all__ = [
    "SeriesRegistryEntry",
    "Frequency",
    "Source",
    "SERIES_REGISTRY",
    "get_series",
    "get_enabled_series",
    "get_series_by_source",
    "list_all_series",
    "register",
    "MacroObservation",
    "SchemaFrequency",
    "SeasonalAdjustment",
    "parse_date_flexible",
    "parse_frequency",
    "parse_seasonal_adjustment",
    "validate_observation",
    "detect_duplicates",
    "detect_missing_values",
    "sort_observations",
    "check_date_ordering",
]