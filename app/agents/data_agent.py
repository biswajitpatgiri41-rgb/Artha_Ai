"""Stub data agent.

The real data layer is not yet implemented.  This module provides a
deterministic stub that can later be swapped out.  It exposes a single
function :func:`get_required_series` that returns a dictionary describing
which series would be needed for a given request.
"""

from __future__ import annotations

from typing import Dict, List

from .schemas import AgentEvidence

__all__ = ["get_required_series"]


def _map_indicator_to_series(indicator: str) -> List[str]:
    """Map a high‑level indicator to underlying series names.

    The mapping is intentionally minimal and can be expanded when real
    data sources are integrated.
    """

    mapping = {
        "CPI": ["cpi_yoy"],
        "food inflation": ["food_inflation_yoy"],
        "core inflation": ["core_inflation_proxy"],
        "GDP": ["gdp_yoy"],
        "IIP": ["iip_yoy"],
        "repo rate": ["repo_rate"],
        "INR/USD": ["inr_usd"],
        "crude oil": ["crude_oil_price"],
        "credit growth": ["credit_growth"],
        "money supply": ["money_supply"],
        "rainfall": ["rainfall"],
        "global interest rates": ["global_interest_rates"],
    }
    return mapping.get(indicator.lower(), [])


def get_required_series(request: str) -> Dict[str, List[str]]:
    """Return a stubbed description of required series.

    Parameters
    ----------
    request:
        A natural language request such as "Analyze current inflation".

    Returns
    -------
    dict
        ``{"required_series": [...], "availability": "UNAVAILABLE", "missing_data": [...], "planned_sources": [...]}``
    """

    # Very naive keyword extraction – sufficient for the stub.
    indicators = [
        kw for kw in [
            "CPI",
            "food inflation",
            "core inflation",
            "GDP",
            "IIP",
            "repo rate",
            "INR/USD",
            "crude oil",
            "credit growth",
            "money supply",
            "rainfall",
            "global interest rates",
        ]
        if kw.lower() in request.lower()
    ]

    series = []
    for ind in indicators:
        series.extend(_map_indicator_to_series(ind))

    # Build the response structure
    response = {
        "required_series": series,
        "availability": "UNAVAILABLE",
        "missing_data": [f"{s} observations" for s in series],
        "planned_sources": ["RBI DBIE", "MoSPI"],
    }
    return response
