"""Policy agent stub.

The agent compares monetary‑policy alternatives using evidence supplied by
upstream agents.  It does not perform quantitative analysis and therefore
returns a provisional assessment when data are missing.
"""

from __future__ import annotations

from typing import List

from .schemas import PolicyAnalysis, PolicyOption


def run_policy(user_input: str, evidence: List[dict]) -> PolicyAnalysis:
    """Return a provisional policy analysis.

    Parameters
    ----------
    user_input:
        Natural language description of the scenario.
    evidence:
        List of evidence dictionaries from upstream agents.
    """

    # Detect if any numeric evidence is present
    numeric_present = any(
        e.get("value") is not None for e in evidence
    )
    if numeric_present:
        status = "INSUFFICIENT_DATA"
    else:
        status = "PROVISIONAL"

    options = [
        PolicyOption(
            name="Hike 50 bp",
            inflation_control="High",
            growth_support="Low",
            fx_effect="Negative",
            financial_conditions="Tightening",
            risks=["Potential slowdown"]
        ),
        PolicyOption(
            name="Hold",
            inflation_control="Medium",
            growth_support="Medium",
            fx_effect="Neutral",
            financial_conditions="Neutral",
            risks=["Inflation persistence"]
        ),
        PolicyOption(
            name="Cut 25 bp",
            inflation_control="Low",
            growth_support="High",
            fx_effect="Positive",
            financial_conditions="Easing",
            risks=["Inflation surge"]
        ),
    ]

    return PolicyAnalysis(
        stance="Provisional assessment based on available evidence.",
        options=options,
        confidence=0.3 if status == "PROVISIONAL" else 0.1,
        evidence=[
            e for e in evidence
        ],
        assumptions=["No quantitative data available.", "Scenario is hypothetical."],
        warnings=["This is a prototype scenario analysis and not an official RBI policy recommendation."]
    )
