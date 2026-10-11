"""
CPI Inflation Forecasting Configuration.

Central configuration for the prediction-first architecture.
Defines target, horizons, features, and data requirements.
"""

from dataclasses import dataclass
from typing import Literal

# ============================================================
# TARGET DEFINITION
# ============================================================

TARGET_SERIES = "cpi_yoy"  # India headline CPI year-over-year inflation
TARGET_FREQUENCY = "monthly"
TARGET_DESCRIPTION = "India headline CPI year-over-year inflation"

# ============================================================
# FORECAST HORIZONS
# ============================================================

HORIZONS = ["h1", "h3", "h6", "h12"]  # 1, 3, 6, 12 months ahead
HORIZON_MONTHS = {"h1": 1, "h3": 3, "h6": 6, "h12": 12}

# ============================================================
# CORE MVP FEATURES (Required for baseline model)
# ============================================================

MVP_FEATURES = [
    "cpi_yoy",           # Target itself (for lag features)
    "food_inflation_yoy", # Food CPI YoY
    "oil_yoy",           # Brent crude YoY change
    "inr_yoy",           # INR/USD YoY change
    "repo_rate",         # RBI repo rate
    "iip_yoy",           # Index of Industrial Production YoY
]

# ============================================================
# EXPANDED FEATURES (Optional, for enhanced models)
# ============================================================

EXPANDED_FEATURES = [
    "wpi_yoy",              # Wholesale Price Index YoY
    "repo_change_3m",       # 3-month repo rate change
    "credit_growth",        # Bank credit growth
    "m3_growth",            # M3 money supply growth
    "us_cpi_yoy",           # US CPI YoY
    "us_policy_rate",       # US Federal Funds Rate
    "rainfall_deviation",   # Monsoon rainfall deviation
    "month_sin",            # Seasonal encoding
    "month_cos",            # Seasonal encoding
]

ALL_FEATURES = MVP_FEATURES + EXPANDED_FEATURES

# ============================================================
# SERIES MAPPING (Canonical ID -> Registry ID)
# ============================================================

SERIES_MAPPING = {
    # MVP series
    "cpi_yoy": "cpi_headline",
    "food_inflation_yoy": "food_inflation",
    "oil_yoy": "brent_crude",       # Derived from brent_crude
    "inr_yoy": "inr_usd",           # Derived from inr_usd
    "repo_rate": "repo_rate",
    "iip_yoy": "iip",
    
    # Expanded series
    "wpi_yoy": "wpi",
    "repo_change_3m": "repo_rate",  # Derived from repo_rate
    "credit_growth": "bank_credit",
    "m3_growth": "m3",
    "us_cpi_yoy": "us_cpi",         # Derived from us_cpi
    "us_policy_rate": "us_policy_rate",
    "rainfall_deviation": "rainfall_deviation",
}

# ============================================================
# REQUIRED MVP SERIES FOR READINESS CHECK
# ============================================================

REQUIRED_MVP_SERIES = [
    "cpi_headline",
    "food_inflation",
    "brent_crude",
    "inr_usd",
    "repo_rate",
    "iip",
]

# ============================================================
# DATA PROCESSING CONSTANTS
# ============================================================

MACRO_MONTHLY_PATH = "data/processed/macro_monthly"
CPI_FEATURES_PATH = "data/processed/cpi_features"

# Minimum observations for training (rule of thumb: 5+ years monthly = 60+)
MIN_OBSERVATIONS_TRAINING = 60

# Maximum allowed missing months in a row
MAX_CONSECUTIVE_MISSING = 3

# ============================================================
# FEATURE ENGINEERING PARAMETERS
# ============================================================

LAG_PERIODS = [1, 2, 3, 6, 12]
ROLLING_WINDOWS = {
    "cpi_ma": [3, 6],
    "oil_vol": [6],
    "inr_vol": [6],
}

SEASONAL_ENCODING = True

# ============================================================
# VALIDATION RULES
# ============================================================

VALIDATION_RULES = {
    "no_future_leakage": True,
    "no_silent_drops": True,
    "frequency_validation": True,
    "duplicate_detection": True,
    "base_year_consistency": True,
}

# ============================================================
# OUTPUT SPECIFICATIONS
# ============================================================

@dataclass(frozen=True)
class MacroMonthlySchema:
    """Schema for the canonical monthly macroeconomic table."""
    date: str                    # YYYY-MM-DD (month end)
    cpi_yoy: float | None        # India CPI YoY %
    food_inflation_yoy: float | None  # Food CPI YoY %
    brent_price: float | None    # Brent crude USD/barrel
    inr_usd: float | None        # INR/USD exchange rate
    repo_rate: float | None      # RBI repo rate %
    iip_yoy: float | None        # IIP YoY %
    # Metadata columns (traceability)
    cpi_source: str | None
    food_source: str | None
    brent_source: str | None
    inr_source: str | None
    repo_source: str | None
    iip_source: str | None

@dataclass(frozen=True)
class CPIFeaturesSchema:
    """Schema for CPI forecasting features."""
    date: str
    # Core features
    cpi_yoy: float | None
    food_inflation_yoy: float | None
    oil_yoy: float | None
    inr_yoy: float | None
    repo_rate: float | None
    iip_yoy: float | None
    # Derived features
    repo_change_1m: float | None
    repo_change_3m: float | None
    real_policy_rate: float | None
    # Seasonality
    month_sin: float | None
    month_cos: float | None
    # Lag features
    cpi_yoy_lag_1: float | None
    cpi_yoy_lag_2: float | None
    cpi_yoy_lag_3: float | None
    cpi_yoy_lag_6: float | None
    cpi_yoy_lag_12: float | None
    food_inflation_yoy_lag_1: float | None
    food_inflation_yoy_lag_2: float | None
    food_inflation_yoy_lag_3: float | None
    food_inflation_yoy_lag_6: float | None
    food_inflation_yoy_lag_12: float | None
    oil_yoy_lag_1: float | None
    oil_yoy_lag_2: float | None
    oil_yoy_lag_3: float | None
    oil_yoy_lag_6: float | None
    oil_yoy_lag_12: float | None
    inr_yoy_lag_1: float | None
    inr_yoy_lag_2: float | None
    inr_yoy_lag_3: float | None
    inr_yoy_lag_6: float | None
    inr_yoy_lag_12: float | None
    # Rolling features
    cpi_ma_3: float | None
    cpi_ma_6: float | None
    oil_vol_6: float | None
    inr_vol_6: float | None
    # Targets
    target_h1: float | None
    target_h3: float | None
    target_h6: float | None
    target_h12: float | None