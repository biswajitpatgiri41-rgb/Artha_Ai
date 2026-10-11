"""LangGraph node wrappers for the research workflow.

Each node updates the shared :class:`ResearchState`, emits operational
events and calls the corresponding agent.  The nodes are intentionally
light‑weight and do not perform any data fetching.
"""

from __future__ import annotations

import datetime
import time
from typing import Any, Dict

from ..agents import (
    planner,
    data_agent,
    growth_agent,
    external_agent,
    econometrics_agent,
    policy_agent,
    critic_agent,
    report_agent,
)
from ..workflows.state import ResearchState

# Simple event model
class ArchitectureEvent(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def _emit(state: ResearchState, event_type: str, **payload: Any) -> None:
    event = ArchitectureEvent(
        run_id=state.run_id,
        timestamp=datetime.datetime.utcnow().isoformat(),
        type=event_type,
        node_id=state.current_node,
        **payload,
    )
    state.events.append(event)


def planner_node(state: ResearchState) -> ResearchState:
    state.current_node = "planner"
    _emit(state, "node_started")
    start = time.time()
    try:
        plan = planner.run_planner(state.question)
        state.plan = plan
        state.status = "PLAN_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "PLAN_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def data_node(state: ResearchState) -> ResearchState:
    state.current_node = "data"
    _emit(state, "node_started")
    start = time.time()
    try:
        data = data_agent.get_required_series(state.plan.objective if state.plan else "")
        state.data = data
        state.status = "DATA_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "DATA_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def inflation_node(state: ResearchState) -> ResearchState:
    state.current_node = "inflation"
    _emit(state, "node_started")
    start = time.time()
    try:
        # No inflation agent implemented; use empty analysis
        from ..agents.schemas import AgentAnalysis
        state.inflation = AgentAnalysis(
            summary="No inflation data available.",
            findings=[],
            evidence=[],
            uncertainties=["Data unavailable"],
            missing_data=[],
            recommended_next_steps=[],
        )
        state.status = "INFLATION_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "INFLATION_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def growth_node(state: ResearchState) -> ResearchState:
    state.current_node = "growth"
    _emit(state, "node_started")
    start = time.time()
    try:
        analysis = growth_agent.run_growth(state.question)
        state.growth = analysis
        state.status = "GROWTH_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "GROWTH_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def external_node(state: ResearchState) -> ResearchState:
    state.current_node = "external"
    _emit(state, "node_started")
    start = time.time()
    try:
        analysis = external_agent.run_external(state.question)
        state.external = analysis
        state.status = "EXTERNAL_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "EXTERNAL_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def econometrics_node(state: ResearchState) -> ResearchState:
    state.current_node = "econometrics"
    _emit(state, "node_started")
    start = time.time()
    try:
        result = econometrics_agent.run_econometrics(state.question)
        state.econometrics = result
        state.status = "ECONOMETRICS_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "ECONOMETRICS_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def policy_node(state: ResearchState) -> ResearchState:
    state.current_node = "policy"
    _emit(state, "node_started")
    start = time.time()
    try:
        evidence = []
        if state.growth:
            evidence.extend([e.dict() for e in state.growth.evidence])
        if state.external:
            evidence.extend([e.dict() for e in state.external.evidence])
        analysis = policy_agent.run_policy(state.question, evidence)
        state.policy = analysis
        state.status = "POLICY_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "POLICY_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def critic_node(state: ResearchState) -> ResearchState:
    state.current_node = "critic"
    _emit(state, "node_started")
    start = time.time()
    try:
        result = critic_agent.run_critic(
            planner_output=state.plan.dict() if state.plan else {},
            data_output=state.data if state.data else {},
            growth_output=state.growth.dict() if state.growth else {},
            external_output=state.external.dict() if state.external else {},
            econometrics_output=state.econometrics if state.econometrics else {},
            policy_output=state.policy.dict() if state.policy else {},
            retrieved_evidence=state.retrieved_evidence,
        )
        state.critic = result
        state.status = "CRITIC_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "CRITIC_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state


def report_node(state: ResearchState) -> ResearchState:
    state.current_node = "report"
    _emit(state, "node_started")
    start = time.time()
    try:
        report = report_agent.run_report(
            planner=state.plan.dict() if state.plan else {},
            data=state.data if state.data else {},
            growth=state.growth,
            external=state.external,
            econometrics=state.econometrics if state.econometrics else {},
            policy=state.policy,
            critic=state.critic.dict() if state.critic else {},
            retrieved_evidence=state.retrieved_evidence,
        )
        state.final_report = report
        state.status = "REPORT_COMPLETED"
        _emit(state, "node_completed", duration_ms=int((time.time() - start) * 1000))
    except Exception as exc:
        state.errors.append(str(exc))
        state.status = "REPORT_FAILED"
        _emit(state, "node_failed", error=str(exc))
    return state
