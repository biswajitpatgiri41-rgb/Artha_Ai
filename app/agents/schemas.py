"""Pydantic models for the agent system.

These models are intentionally lightweight and focus on the data that the
agents will exchange.  They are used for validation and type safety across
the project.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    objective: str
    tasks: List[str]
    required_indicators: List[str]
    required_agents: List[str]
    requires_scenario: bool = False
    assumptions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class AgentEvidence(BaseModel):
    claim: str
    series_id: Optional[str] = None
    source: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[str] = None


class AgentAnalysis(BaseModel):
    summary: str
    findings: List[str]
    evidence: List[AgentEvidence]
    uncertainties: List[str]
    missing_data: List[str]
    recommended_next_steps: List[str]


class PolicyOption(BaseModel):
    name: str
    inflation_control: str
    growth_support: str
    fx_effect: str
    financial_conditions: str
    risks: List[str]


class PolicyAnalysis(BaseModel):
    stance: str
    options: List[PolicyOption]
    confidence: float
    evidence: List[AgentEvidence]
    assumptions: List[str]
    warnings: List[str]


class CriticResult(BaseModel):
    status: str  # PASS or FAIL
    issues: List[str]
    unsupported_claims: List[str]
    missing_sources: List[str]
    repair_actions: List[str]
    quantitative_validation: dict = Field(default_factory=dict)
    evidence_validation: List[dict] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    overall_status: str = "NOT_ASSESSED"


class ReportResult(BaseModel):
    executive_summary: str
    current_state: str
    inflation_view: str
    growth_view: str
    external_view: str
    scenario_view: str
    policy_view: str
    uncertainties: List[str]
    sources: List[str]
    disclaimer: str
    model_evidence: List[dict] = Field(default_factory=list)
    document_evidence: List[dict] = Field(default_factory=list)
