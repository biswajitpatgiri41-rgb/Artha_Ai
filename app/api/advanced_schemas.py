"""Typed contracts for future model-backed research modules.

These schemas describe outputs; they do not make unavailable models appear operational.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RegimeLabel(StrEnum):
    NORMAL_INFLATION = "NORMAL INFLATION"
    SUPPLY_SHOCK_INFLATION = "SUPPLY-SHOCK INFLATION"
    DEMAND_PRESSURE = "DEMAND PRESSURE"
    STAGFLATION = "STAGFLATION"


class RegimeEvidence(BaseModel):
    source: str
    reference: str
    excerpt: str | None = None


class RegimeRecord(BaseModel):
    regime: RegimeLabel
    start_date: date | None = None
    end_date: date | None = None
    probability: float = Field(ge=0, le=1)
    model_version: str = Field(min_length=1, max_length=100)
    data_vintage: str = Field(min_length=1, max_length=100)
    evidence: list[RegimeEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RegimeOutput(BaseModel):
    status: str
    regimes: list[RegimeRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RegisteredModelStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    CHALLENGER = "CHALLENGER"
    CHAMPION = "CHAMPION"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class ModelRegistryRecord(BaseModel):
    model_name: str
    version: str
    target: str
    forecast_horizons: list[int] = Field(min_length=1)
    training_cutoff: date
    data_vintage: str
    feature_list: list[str]
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    backtest_metrics: dict[str, float] = Field(default_factory=dict)
    artifact_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    library_versions: dict[str, str] = Field(default_factory=dict)
    git_commit: str | None = None
    status: RegisteredModelStatus
    created_at: datetime


class ModelRegistryOutput(BaseModel):
    status: str
    models: list[ModelRegistryRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DataQualityStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    STALE = "STALE"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT CONFIGURED"


class DataQualityChecks(BaseModel):
    missing_observations: bool | None = None
    duplicates: bool | None = None
    unit_validation: bool | None = None
    base_year_consistency: bool | None = None
    release_freshness: bool | None = None


class DataQualitySeries(BaseModel):
    series_id: str
    source: str
    health: DataQualityStatus
    last_observation: date | None = None
    last_retrieval: datetime | None = None
    release_date: date | None = None
    data_vintage: str | None = None
    observation_count: int = Field(ge=0)
    unit: str | None = None
    base_year: str | None = None
    validation_issues: list[str] | None = None
    manifest_status: str | None = None
    checks: DataQualityChecks
    note: str


class DataQualityOutput(BaseModel):
    as_of: datetime
    series: list[DataQualitySeries]
    validation_reports: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
