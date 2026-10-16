"""
Central Economic Series Registry.

This module defines the canonical macroeconomic series used throughout the
Agentic Monetary Policy & Inflation Simulator for India.

Each series entry maps a logical canonical identifier to provider-specific
identifiers, metadata, and configuration. Provider IDs marked as TODO/UNVERIFIED
must be resolved from official source documentation before enabling.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Frequency(str, Enum):
    """Observation frequency."""
    ANNUAL = "A"
    QUARTERLY = "Q"
    MONTHLY = "M"
    WEEKLY = "W"
    DAILY = "D"
    FORTNIGHTLY = "F"
    IRREGULAR = "I"


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


@dataclass(frozen=True)
class SeriesRegistryEntry:
    """Canonical series registry entry."""
    canonical_id: str
    description: str
    preferred_source: Source
    provider_series_id: str  # Provider-specific identifier (TODO/UNVERIFIED if unknown)
    frequency: Frequency
    unit: str
    base_year: Optional[str] = None
    source_url: Optional[str] = None
    enabled: bool = False  # Only True when provider_series_id is verified
    alternative_sources: dict[Source, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.provider_series_id.upper().startswith("TODO") or self.provider_series_id.upper().startswith("UNVERIFIED"):
            object.__setattr__(self, 'enabled', False)


# ============================================================
# SERIES REGISTRY - Canonical Macroeconomic Series for India
# ============================================================

SERIES_REGISTRY: dict[str, SeriesRegistryEntry] = {}

def register(series: SeriesRegistryEntry) -> None:
    """Register a series in the global registry."""
    SERIES_REGISTRY[series.canonical_id] = series


# --- INFLATION ---
register(SeriesRegistryEntry(
    canonical_id="cpi_headline",
    description="Consumer Price Index (CPI) Headline Inflation - All India",
    preferred_source=Source.MOSPI,
    provider_series_id="TODO: Verify MoSPI CPI series ID",
    frequency=Frequency.MONTHLY,
    unit="index_2024=100",
    base_year="2024=100",
    source_url="https://mospi.gov.in/",
    enabled=False,
    alternative_sources={
        Source.RBI: "TODO: Verify RBI CPI series ID",
        Source.WORLD_BANK: "FP.CPI.TOTL.ZG",
    }
))

# Forecast target derived from the index. Keep it separate so index levels and
# year-over-year inflation can never be silently mixed by a model.
register(SeriesRegistryEntry(
    canonical_id="cpi_yoy",
    description="India headline CPI year-over-year inflation (derived from the index)",
    preferred_source=Source.MOSPI,
    provider_series_id="DERIVED:cpi_headline",
    frequency=Frequency.MONTHLY,
    unit="percent",
    base_year="2024=100",
    source_url="https://mospi.gov.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="food_inflation",
    description="Food and Beverages CPI inflation - All India (CFPI 2012-base)",
    preferred_source=Source.MOSPI,
    provider_series_id="MoSPI CFPI 2012-base combined YoY",
    frequency=Frequency.MONTHLY,
    unit="percent",
    base_year="2012=100",
    source_url="https://mospi.gov.in/",
    enabled=True,
))

register(SeriesRegistryEntry(
    canonical_id="core_inflation_proxy",
    description="CPI Excluding Food and Fuel (Core Inflation Proxy)",
    preferred_source=Source.MOSPI,
    provider_series_id="TODO: Verify MoSPI Core CPI series ID",
    frequency=Frequency.MONTHLY,
    unit="index_2024=100",
    base_year="2024=100",
    source_url="https://mospi.gov.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="wpi",
    description="Wholesale Price Index (WPI) - All Commodities",
    preferred_source=Source.MOSPI,
    provider_series_id="TODO: Verify MoSPI WPI series ID",
    frequency=Frequency.MONTHLY,
    unit="index_2011=100",
    base_year="2011-12",
    source_url="https://eaindustry.nic.in/",
    enabled=False,
    alternative_sources={
        Source.RBI: "TODO: Verify RBI WPI series ID",
    }
))

# --- ACTIVITY ---
register(SeriesRegistryEntry(
    canonical_id="gdp",
    description="Gross Domestic Product (GDP) at Constant Prices",
    preferred_source=Source.MOSPI,
    provider_series_id="TODO: Verify MoSPI GDP series ID",
    frequency=Frequency.QUARTERLY,
    unit="crore_rupees_constant",
    base_year="2011-12",
    source_url="https://mospi.gov.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="gva",
    description="Gross Value Added (GVA) at Basic Prices - Constant",
    preferred_source=Source.MOSPI,
    provider_series_id="TODO: Verify MoSPI GVA series ID",
    frequency=Frequency.QUARTERLY,
    unit="crore_rupees_constant",
    base_year="2011-12",
    source_url="https://mospi.gov.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="iip",
    description="Index of Industrial Production (IIP) - General Index",
    preferred_source=Source.MOSPI,
    provider_series_id="TODO: Verify MoSPI IIP series ID",
    frequency=Frequency.MONTHLY,
    unit="index_2022-23=100",
    base_year="2022-23",
    source_url="https://mospi.gov.in/",
    enabled=False,
))

# --- POLICY ---
register(SeriesRegistryEntry(
    canonical_id="repo_rate",
    description="Policy Repo Rate",
    preferred_source=Source.RBI,
    # RBI identifies this as a downloadable DBIE report/table rather than a
    # documented API series ID. Preserve its official report name verbatim.
    provider_series_id="DBIE report: Major Monetary Policy Measures – Bank Rate, CRR & SLR (Key Rates)",
    frequency=Frequency.IRREGULAR,
    unit="percent",
    source_url="https://data.rbi.org.in/#/dbie/reports/Statistics/Financial%20Sector/Key%20Rates",
    enabled=True,
))

register(SeriesRegistryEntry(
    canonical_id="sdf_rate",
    description="Standing Deposit Facility (SDF) Rate",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI SDF Rate series ID",
    frequency=Frequency.DAILY,
    unit="percent",
    source_url="https://www.rbi.org.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="msf_rate",
    description="Marginal Standing Facility (MSF) Rate",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI MSF Rate series ID",
    frequency=Frequency.DAILY,
    unit="percent",
    source_url="https://www.rbi.org.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="crr",
    description="Cash Reserve Ratio (CRR)",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI CRR series ID",
    frequency=Frequency.DAILY,
    unit="percent",
    source_url="https://www.rbi.org.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="slr",
    description="Statutory Liquidity Ratio (SLR)",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI SLR series ID",
    frequency=Frequency.DAILY,
    unit="percent",
    source_url="https://www.rbi.org.in/",
    enabled=False,
))

# --- EXTERNAL ---
register(SeriesRegistryEntry(
    canonical_id="inr_usd",
    description="INR/USD Exchange Rate (Reference Rate)",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI INR/USD series ID",
    frequency=Frequency.DAILY,
    unit="inr_per_usd",
    source_url="https://www.rbi.org.in/",
    enabled=False,
    alternative_sources={
        Source.FRED: "DEXINUS",
    }
))

register(SeriesRegistryEntry(
    canonical_id="forex_reserves",
    description="Foreign Exchange Reserves (Total)",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI Forex Reserves series ID",
    frequency=Frequency.WEEKLY,
    unit="million_usd",
    source_url="https://www.rbi.org.in/",
    enabled=False,
    alternative_sources={
        Source.WORLD_BANK: "FI.RES.TOTL.CD",
    }
))

register(SeriesRegistryEntry(
    canonical_id="brent_crude",
    description="Brent Crude Oil Price",
    preferred_source=Source.FRED,
    provider_series_id="DCOILBRENTEU",
    frequency=Frequency.DAILY,
    unit="usd_per_barrel",
    source_url="https://fred.stlouisfed.org/series/DCOILBRENTEU",
    enabled=True,
))

register(SeriesRegistryEntry(
    canonical_id="global_rates",
    description="Global Interest Rate Composite (placeholder)",
    preferred_source=Source.FRED,
    provider_series_id="TODO: Define composite or specific series",
    frequency=Frequency.MONTHLY,
    unit="percent",
    source_url="https://fred.stlouisfed.org/",
    enabled=False,
))

# --- FINANCIAL ---
register(SeriesRegistryEntry(
    canonical_id="bank_credit",
    description="Bank Credit (Outstanding) - Scheduled Commercial Banks",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI Bank Credit series ID",
    frequency=Frequency.FORTNIGHTLY,
    unit="crore_rupees",
    source_url="https://www.rbi.org.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="m3",
    description="Broad Money (M3) Stock",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI M3 series ID",
    frequency=Frequency.FORTNIGHTLY,
    unit="crore_rupees",
    source_url="https://www.rbi.org.in/",
    enabled=False,
))

register(SeriesRegistryEntry(
    canonical_id="government_bond_yield",
    description="10-Year Government Bond Yield (India)",
    preferred_source=Source.RBI,
    provider_series_id="TODO: Verify RBI G-Sec Yield series ID",
    frequency=Frequency.DAILY,
    unit="percent",
    source_url="https://www.rbi.org.in/",
    enabled=False,
    alternative_sources={
        Source.FRED: "IRLTLT01INM156N",
    }
))

# --- SUPPLY ---
register(SeriesRegistryEntry(
    canonical_id="rainfall_deviation",
    description="Monsoon Rainfall Deviation from Long Period Average (LPA)",
    preferred_source=Source.IMD,
    provider_series_id="TODO: Verify IMD rainfall series ID",
    frequency=Frequency.ANNUAL,
    unit="percent_deviation",
    source_url="https://mausam.imd.gov.in/",
    enabled=False,
))

# --- GLOBAL ---
register(SeriesRegistryEntry(
    canonical_id="us_policy_rate",
    description="US Federal Funds Rate (Effective)",
    preferred_source=Source.FRED,
    provider_series_id="FEDFUNDS",
    frequency=Frequency.MONTHLY,
    unit="percent",
    source_url="https://fred.stlouisfed.org/series/FEDFUNDS",
    enabled=True,
))

register(SeriesRegistryEntry(
    canonical_id="us_cpi",
    description="US Consumer Price Index (All Items)",
    preferred_source=Source.FRED,
    provider_series_id="CPIAUCSL",
    frequency=Frequency.MONTHLY,
    unit="index_1982=100",
    base_year="1982-84",
    source_url="https://fred.stlouisfed.org/series/CPIAUCSL",
    enabled=True,
))

# Lower-frequency World Bank series are retained as context only. They must not
# be interpolated or joined into the monthly CPI training panel.
register(SeriesRegistryEntry(
    canonical_id="india_cpi_inflation_annual_wb",
    description="India consumer price inflation (annual, World Bank context series)",
    preferred_source=Source.WORLD_BANK,
    provider_series_id="FP.CPI.TOTL.ZG",
    frequency=Frequency.ANNUAL,
    unit="percent",
    source_url="https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=IN",
    enabled=True,
))

register(SeriesRegistryEntry(
    canonical_id="india_gdp_growth_annual_wb",
    description="India GDP growth (annual, World Bank context series)",
    preferred_source=Source.WORLD_BANK,
    provider_series_id="NY.GDP.MKTP.KD.ZG",
    frequency=Frequency.ANNUAL,
    unit="percent",
    source_url="https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=IN",
    enabled=True,
))

register(SeriesRegistryEntry(
    canonical_id="world_gdp_growth_annual_wb",
    description="World GDP growth (annual, World Bank context series)",
    preferred_source=Source.WORLD_BANK,
    provider_series_id="NY.GDP.MKTP.KD.ZG",
    frequency=Frequency.ANNUAL,
    unit="percent",
    source_url="https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=1W",
    enabled=True,
))

# --- COMMODITIES ---
register(SeriesRegistryEntry(
    canonical_id="brent_crude",
    description="Europe Brent Spot Price FOB (Dollars per Barrel)",
    preferred_source=Source.EIA,
    provider_series_id="RBRTE",
    frequency=Frequency.DAILY,
    unit="usd_per_barrel",
    source_url="https://api.eia.gov/v2/petroleum/pri/spt/data/",
    enabled=True,
    alternative_sources={
        Source.FRED: "DCOILBRENTEU",
    }
))


def get_series(canonical_id: str) -> Optional[SeriesRegistryEntry]:
    """Get a series entry by canonical ID."""
    return SERIES_REGISTRY.get(canonical_id)


def get_enabled_series() -> dict[str, SeriesRegistryEntry]:
    """Get all enabled series entries."""
    return {k: v for k, v in SERIES_REGISTRY.items() if v.enabled}


def get_series_by_source(source: Source) -> dict[str, SeriesRegistryEntry]:
    """Get all series entries for a given source (including alternatives)."""
    result = {}
    for k, v in SERIES_REGISTRY.items():
        if v.preferred_source == source or source in v.alternative_sources:
            result[k] = v
    return result


def list_all_series() -> list[SeriesRegistryEntry]:
    """List all registered series."""
    return list(SERIES_REGISTRY.values())
