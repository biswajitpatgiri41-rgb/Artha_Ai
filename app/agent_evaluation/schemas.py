from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class BenchmarkCategory(StrEnum):
    INFLATION = "Inflation"
    GROWTH = "Growth"
    EXTERNAL_SECTOR = "External Sector"
    FORECASTING = "Forecasting"
    POLICY = "Policy"
    MISSING_DATA = "Missing Data"
    WRONG_UNITS = "Wrong Units"
    STALE_OBSERVATIONS = "Stale Observations"
    BASE_YEAR_CONFLICTS = "Base-Year Conflicts"
    EXTREME_SCENARIOS = "Extreme Scenarios"
    UNSUPPORTED_CAUSAL_CLAIMS = "Unsupported Causal Claims"
    TOOL_FAILURES = "Tool Failures"


class AgentBenchmarkQuestion(BaseModel):
    question_id: str = Field(min_length=1, max_length=100)
    category: BenchmarkCategory
    question: str = Field(min_length=1, max_length=4000)
    expected_tools: list[str] = Field(default_factory=list)
    expected_result: dict = Field(default_factory=dict)


class AgentBenchmarkCaseResult(BaseModel):
    benchmark_run_id: str
    agent: str
    question_id: str
    expected_tools: list[str]
    actual_tools: list[str]
    result: dict
    warnings: list[str] = Field(default_factory=list)
    runtime_ms: int = Field(ge=0)
    model_version: str | None = None
    evaluated_at: datetime


class AgentBenchmarkScorecard(BaseModel):
    benchmark_run_id: str
    agent: str
    model_version: str | None = None
    question_count: int = Field(ge=0)
    tool_selection_accuracy: float | None = Field(default=None, ge=0, le=1)
    numerical_faithfulness: float | None = Field(default=None, ge=0, le=1)
    citation_accuracy: float | None = Field(default=None, ge=0, le=1)
    schema_validity: float | None = Field(default=None, ge=0, le=1)
    unsupported_claims: int | None = Field(default=None, ge=0)
    failure_handling: float | None = Field(default=None, ge=0, le=1)
    results: list[AgentBenchmarkCaseResult] = Field(default_factory=list)
