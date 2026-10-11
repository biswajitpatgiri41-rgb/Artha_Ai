"""Econometrics agent stub.

The agent only determines what econometric operation would be required
for a given user request.  It does not perform any forecasting.
"""

from __future__ import annotations

from typing import Dict, List

from .schemas import AgentAnalysis


def run_econometrics(request: str) -> Dict[str, object]:
    """Return a deterministic description of the required econometric method.

    Parameters
    ----------
    request:
        Natural language description of the analysis to perform.
    """

    # Very simple keyword mapping
    method = "MODEL_NOT_CONNECTED"
    features: List[str] = []
    if "cpi" in request.lower() and "oil" in request.lower():
        method = "SARIMAX/VAR/local projection"
        features = ["cpi_yoy", "oil_yoy", "inr_yoy", "repo_rate"]
    elif "inflation" in request.lower() and "growth" in request.lower():
        method = "VAR"
        features = ["inflation_yoy", "gdp_yoy", "repo_rate"]
    else:
        method = "MODEL_NOT_CONNECTED"
        features = []

    return {
        "requested_analysis": request,
        "recommended_method": method,
        "required_features": features,
        "status": method if method != "MODEL_NOT_CONNECTED" else "MODEL_NOT_CONNECTED",
        "missing_data": [f"{f} observations" for f in features],
    }
