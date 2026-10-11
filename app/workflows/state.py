"""Shared state for the LangGraph research workflow.

The :class:`ResearchState` is a simple serialisable container that holds
all intermediate results and metadata.  It deliberately avoids storing
any secrets or hidden LLM reasoning.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..agents.schemas import (
    ResearchPlan,
    AgentAnalysis,
    PolicyAnalysis,
    CriticResult,
    ReportResult,
)


@dataclass
class ResearchState:
    # Core identifiers
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question: str = ""
    status: str = "INITIALIZED"

    # Sub‑states
    plan: Optional[ResearchPlan] = None
    data: Optional[Dict[str, Any]] = None
    inflation: Optional[AgentAnalysis] = None
    growth: Optional[AgentAnalysis] = None
    external: Optional[AgentAnalysis] = None
    econometrics: Optional[Dict[str, Any]] = None
    retrieved_evidence: List[Dict[str, Any]] = field(default_factory=list)
    policy: Optional[PolicyAnalysis] = None
    critic: Optional[CriticResult] = None
    final_report: Optional[ReportResult] = None

    # Execution metadata
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_node: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON‑serialisable representation of the state."""
        return {
            "run_id": self.run_id,
            "question": self.question,
            "status": self.status,
            "plan": self.plan.dict() if self.plan else None,
            "data": self.data,
            "inflation": self.inflation.dict() if self.inflation else None,
            "growth": self.growth.dict() if self.growth else None,
            "external": self.external.dict() if self.external else None,
            "econometrics": self.econometrics,
            "retrieved_evidence": self.retrieved_evidence,
            "policy": self.policy.dict() if self.policy else None,
            "critic": self.critic.dict() if self.critic else None,
            "final_report": self.final_report.dict() if self.final_report else None,
            "warnings": self.warnings,
            "errors": self.errors,
            "events": self.events,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_node": self.current_node,
        }
