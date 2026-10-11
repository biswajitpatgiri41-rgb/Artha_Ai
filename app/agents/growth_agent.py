"""Growth agent stub.

The agent analyses growth‑side indicators.  It does not access real data
and therefore never returns numeric observations.  Instead it
identifies required evidence, lists missing data, and records
qualitative uncertainties.
"""

from __future__ import annotations

from typing import List

from .schemas import AgentAnalysis, AgentEvidence


def run_growth(user_input: str) -> AgentAnalysis:
    """Return a qualitative growth analysis.

    Parameters
    ----------
    user_input:
        Natural language description of the scenario.
    """

    # Identify indicators mentioned in the input
    indicators = []
    if "gdp" in user_input.lower() or "gva" in user_input.lower():
        indicators.append("GDP/GVA")
    if "iip" in user_input.lower():
        indicators.append("IIP")
    if "credit" in user_input.lower():
        indicators.append("credit growth")
    if "consumption" in user_input.lower() or "activity" in user_input.lower():
        indicators.append("consumption/activity proxies")
    if "financial" in user_input.lower():
        indicators.append("financial conditions")

    missing = [f"{ind} observations" for ind in indicators]
    uncertainties = ["Data availability", "Seasonal adjustments", "Structural changes"]
    evidence: List[AgentEvidence] = []
    return AgentAnalysis(
        summary="Qualitative growth assessment.",
        findings=[f"Identified indicators: {', '.join(indicators)}"],
        evidence=evidence,
        uncertainties=uncertainties,
        missing_data=missing,
        recommended_next_steps=["Acquire real data for the identified indicators."]
    )
