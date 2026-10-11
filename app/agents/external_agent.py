"""External factors agent stub.

The agent analyses external economic drivers such as FX, oil and
global interest rates.  It does not access real data and therefore never
returns numeric observations.
"""

from __future__ import annotations

from typing import List

from .schemas import AgentAnalysis


def run_external(user_input: str) -> AgentAnalysis:
    """Return a qualitative external analysis.

    Parameters
    ----------
    user_input:
        Natural language description of the scenario.
    """

    indicators = []
    if "inr" in user_input.lower() or "usd" in user_input.lower():
        indicators.append("INR/USD")
    if "oil" in user_input.lower() or "brent" in user_input.lower():
        indicators.append("crude oil")
    if "fed" in user_input.lower() or "federal" in user_input.lower() or "interest" in user_input.lower():
        indicators.append("global interest rates")
    if "inflation" in user_input.lower() and "external" in user_input.lower():
        indicators.append("external inflation pressure")
    if "fx" in user_input.lower():
        indicators.append("FX transmission")

    missing = [f"{ind} observations" for ind in indicators]
    uncertainties = ["Data availability", "Exchange rate volatility", "Commodity price swings"]
    return AgentAnalysis(
        summary="Qualitative external assessment.",
        findings=[f"Identified external indicators: {', '.join(indicators)}"],
        evidence=[],
        uncertainties=uncertainties,
        missing_data=missing,
        recommended_next_steps=["Acquire real data for the identified external indicators."]
    )
