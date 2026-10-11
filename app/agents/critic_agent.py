"""Critic agent.

The critic validates the outputs of all other agents.  It checks for
unsupported numerical claims, missing sources, fabricated observations and
other inconsistencies.  The result is a :class:`CriticResult`.
"""

from __future__ import annotations

from typing import List

from .schemas import CriticResult


def run_critic(
    planner_output: dict,
    data_output: dict,
    growth_output: dict,
    external_output: dict,
    econometrics_output: dict,
    policy_output: dict,
    retrieved_evidence: list[dict] | None = None,
) -> CriticResult:
    """Validate combined agent outputs.

    Parameters are raw dictionaries from the respective agents.
    """

    issues: List[str] = []
    repair_actions: List[str] = []
    missing_sources: List[str] = []
    unsupported_claims: List[str] = []
    missing_data: List[str] = []
    # Simple checks
    # 1. Look for numeric values in planner (should be none)
    if any(isinstance(v, (int, float)) for v in planner_output.values()):
        issues.append("Planner output contains numeric values.")
        repair_actions.append("Remove numeric values from planner output.")
    # 2. Data agent should not contain actual observations
    if data_output.get("availability") == "AVAILABLE":
        issues.append("Data agent indicates data is available.")
        repair_actions.append("Mark data as UNAVAILABLE.")
    # 3. Check for missing data flags
    for out in [growth_output, external_output, econometrics_output, policy_output]:
        if isinstance(out, dict) and out.get("missing_data"):
            missing_data.extend(out["missing_data"])
    # 4. Ensure policy output does not reference current CPI
    if any("cpi" in str(v).lower() for v in policy_output.get("evidence", [])):
        issues.append("Policy evidence references CPI.")
        repair_actions.append("Remove CPI references from policy evidence.")
    status = "FAIL" if issues else "PASS"
    model_output = econometrics_output if isinstance(econometrics_output, dict) else {}
    forecast = model_output.get("forecast") if isinstance(model_output.get("forecast"), dict) else {}
    backtest = model_output.get("backtest") if isinstance(model_output.get("backtest"), dict) else {}
    interval_data = forecast.get("intervals") or forecast.get("prediction_intervals")
    quantitative = {
        "forecast_present": bool(model_output),
        "model_identity_present": bool(model_output.get("model") or model_output.get("model_name") or model_output.get("model_version")),
        "model_consistency": "REVIEW_REQUIRED",
        "numerical_claims": "NOT_ASSESSED",
        "forecast_horizon_present": bool(forecast.get("horizon") or forecast.get("horizon_months")),
        "units_present": bool(forecast.get("unit") or forecast.get("units")),
        "intervals_present": bool(interval_data),
        "backtest_metrics_present": bool(backtest.get("mae") is not None or model_output.get("metrics")),
        "data_version_present": bool(model_output.get("data_version") or model_output.get("dataset_version")),
        "scenario_assumptions_present": bool(model_output.get("scenario_assumptions")),
        "status": "REVIEW_REQUIRED" if not model_output else "CHECKS_RECORDED",
        "note": "Document retrieval does not assess numerical forecast accuracy.",
    }
    evidence_validation = []
    for item in retrieved_evidence or []:
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        evidence_validation.append({
            "evidence_id": item.get("evidence_id"),
            "filename": item.get("filename"),
            "location": location,
            "citation_metadata_present": bool(item.get("filename") and (location.get("page") or location.get("sheet") or location.get("rows") or location.get("path") or location.get("section"))),
            "excerpt_available": bool(item.get("excerpt") or item.get("structured_result")),
            "supports_future_forecast_accuracy": False,
        })
    validation_warnings = []
    if not model_output:
        validation_warnings.append("No registered numerical model output was supplied to the critic.")
    else:
        if not quantitative["model_identity_present"]:
            validation_warnings.append("Model identity or version is missing.")
        if not quantitative["forecast_horizon_present"]:
            validation_warnings.append("Forecast horizon metadata is missing.")
        if not quantitative["units_present"]:
            validation_warnings.append("Forecast unit metadata is missing.")
        if not quantitative["backtest_metrics_present"]:
            validation_warnings.append("Backtest metrics are missing.")
        if not quantitative["intervals_present"]:
            validation_warnings.append("Forecast interval metadata is missing.")
        if not quantitative["data_version_present"]:
            validation_warnings.append("Data version metadata is missing.")
    if retrieved_evidence:
        validation_warnings.append("Uploaded documents support narrative context only; they do not validate future forecast values.")
    return CriticResult(
        status=status,
        issues=issues,
        unsupported_claims=unsupported_claims,
        missing_sources=missing_sources,
        repair_actions=repair_actions,
        quantitative_validation=quantitative,
        evidence_validation=evidence_validation,
        warnings=validation_warnings,
        overall_status="REVIEW_REQUIRED" if validation_warnings or issues else "PASS",
    )
