from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.series_registry import SERIES_REGISTRY
from app.models.enriched_forecast import VARIANTS, enriched_forecast, packaged_model_registry
from app.models.final_package import (
    ModelPackageIntegrityError,
    final_model_explainability,
    final_model_forecast,
    final_model_registry,
)
from app.models.p2_cpi_benchmark import P2ModelNotReadyError, p2_forecast, p2_model_registry
from app.tools.research import ROOT, catalog, load_series, rolling_backtest, seasonal_naive, simulate_scenario
from app.agents.critic_agent import run_critic
from app.evidence.schemas import SearchRequest
from app.evidence.service import get_evidence_service
from app.evidence.events import emit_event

router = APIRouter(tags=["research"])
RUNS_DIR = ROOT / "data" / "runs"


class ScenarioRequest(BaseModel):
    base_inflation: float = Field(ge=-20, le=100, description="CPI inflation baseline, percent")
    oil_change_pct: float = Field(default=0, ge=-200, le=200)
    inr_change_pct: float = Field(default=0, ge=-50, le=50)
    food_shock_pp: float = Field(default=0, ge=-20, le=20)
    repo_change_bp: float = Field(default=0, ge=-500, le=500)
    horizon_months: int = Field(default=6, ge=1, le=24)


class ForecastRequest(BaseModel):
    series_id: str = "cpi_yoy"
    horizon: int = Field(default=6, ge=1, le=24)
    model: str = "seasonal_naive"
    variant: str = "base"


class BacktestRequest(BaseModel):
    series_id: str = "cpi_yoy"
    horizon: int = Field(default=1, ge=1, le=12)
    min_train: int = Field(default=24, ge=2)


class ResearchScenario(BaseModel):
    name: str = Field(default="External shock", max_length=120)
    oil_pct: float = Field(default=0, ge=-200, le=200)
    inr_pct: float = Field(default=0, ge=-50, le=50)
    food_pp: float = Field(default=0, ge=-20, le=20)
    policy_rate_change_bp: float = Field(default=0, ge=-500, le=500)


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=2000)
    horizon_months: int = Field(default=6, ge=1, le=24)
    scenarios: list[ResearchScenario] = Field(default_factory=list, max_length=10)
    use_uploaded_evidence: bool = False
    evidence_run_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


@router.get("/research")
def list_research_runs(limit: int = 20):
    """List persisted research runs; never return bundled example records."""
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    if not RUNS_DIR.is_dir():
        return {"runs": []}
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(run, dict) and run.get("run_id"):
                runs.append(run)
        except (OSError, json.JSONDecodeError):
            continue
    return {"runs": runs}


def _read_run(run_id: str) -> dict:
    try:
        uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Research run not found") from exc
    path = RUNS_DIR / f"{run_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Research run not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Research run record could not be read") from exc


@router.get("/series")
def get_series_catalog():
    return {"mode": "project_data", "series": catalog()}


@router.get("/series/{series_id}")
def get_series_observations(series_id: str, limit: int = 500):
    if series_id not in SERIES_REGISTRY:
        raise HTTPException(status_code=404, detail="Series is not registered")
    if not 1 <= limit <= 5000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 5000")
    observations = load_series(series_id)
    return {"series_id": series_id, "mode": "project_data", "observations": [o.__dict__ for o in observations[-limit:]],
            "available": bool(observations), "count": len(observations)}


@router.get("/forecast/models")
def get_packaged_forecast_models():
    """Return model variants and holdout metrics bundled with the CPI package."""
    try:
        return packaged_model_registry()
    except (ModelPackageIntegrityError, OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="Packaged model registry is unavailable") from exc


@router.get("/forecast/final/models")
def get_final_forecast_models():
    """Expose metrics from the final, checksum-verified model package."""
    try:
        return final_model_registry()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_unavailable"}) from exc
    except (ModelPackageIntegrityError, OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_package_invalid"}) from exc


@router.get("/forecast/p2/models")
def get_p2_forecast_models():
    """Expose the separately licensed P2 research benchmark and its provenance."""
    try:
        return p2_model_registry()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "status": "model_package_invalid"},
        ) from exc


@router.get("/forecast/p2")
def get_p2_forecast(model: str = "p2_arima", horizon: int = 1):
    """Return an optional one-month forecast from an imported P2 model bundle."""
    try:
        return p2_forecast(model, horizon)
    except P2ModelNotReadyError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "status": "model_not_ready"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "status": "model_unavailable"},
        ) from exc


@router.get("/forecast/final")
def get_final_forecast(model: str = "ensemble", variant: str = "mospi_2024_base", horizon: int = 6):
    """Return a stored final-package forecast, with its actual model/data vintage."""
    try:
        return final_model_forecast(model, variant, horizon)
    except ModelPackageIntegrityError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_package_invalid"}) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail={"message": "Final model artifact JSON is invalid.", "status": "model_package_invalid"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "status": "forecast_not_available"}) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_unavailable"}) from exc
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail={"message": "Final model artifact could not be read.", "status": "model_package_invalid"}) from exc


@router.get("/forecast/final/explainability")
def get_final_forecast_explainability(model: str = "xgboost", variant: str = "mospi_2024_base", horizon: int = 6):
    try:
        return final_model_explainability(model, variant, horizon)
    except ModelPackageIntegrityError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_package_invalid"}) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail={"message": "Explainability artifact JSON is invalid.", "status": "model_package_invalid"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "status": "explanation_not_available"}) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_unavailable"}) from exc
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail={"message": "Explainability artifact could not be read.", "status": "model_package_invalid"}) from exc


@router.get("/forecast")
def get_forecast(series_id: str = "cpi_yoy", horizon: int = 6,
                 model: str = "seasonal_naive", variant: str = "base"):
    if series_id not in SERIES_REGISTRY:
        raise HTTPException(status_code=404, detail="Series is not registered")
    try:
        if model != "seasonal_naive":
            if series_id != "cpi_yoy":
                raise ValueError("Packaged trained models forecast only cpi_yoy")
            return enriched_forecast(model, variant, horizon)
        return seasonal_naive(series_id, horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "status": "data_unavailable"}) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "model_unavailable"}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc), "status": "dependency_unavailable"}) from exc
    except (KeyError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "status": "model_input_error"}) from exc


@router.post("/forecast")
def post_forecast(request: ForecastRequest):
    return get_forecast(request.series_id, request.horizon, request.model, request.variant)


@router.get("/backtest")
def get_backtest(series_id: str = "cpi_yoy", horizon: int = 1, min_train: int = 24):
    if series_id not in SERIES_REGISTRY:
        raise HTTPException(status_code=404, detail="Series is not registered")
    try:
        return rolling_backtest(series_id, horizon, min_train)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "status": "data_unavailable"}) from exc


@router.post("/backtest")
def post_backtest(request: BacktestRequest):
    return get_backtest(request.series_id, request.horizon, request.min_train)


@router.post("/simulate")
def post_simulation(request: ScenarioRequest):
    return simulate_scenario(request.base_inflation, request.oil_change_pct,
                             request.inr_change_pct, request.food_shock_pp,
                             request.repo_change_bp, request.horizon_months)


@router.get("/sources")
def get_sources():
    seen: dict[str, dict] = {}
    for series in catalog():
        source_id = series["source"]
        item = seen.setdefault(source_id, {"id": source_id, "series_count": 0,
                                          "available_series_count": 0, "series": []})
        item["series_count"] += 1
        item["available_series_count"] += int(series["available"])
        item["series"].append(series["id"])
    return {"sources": list(seen.values())}


@router.post("/research")
async def create_research_run(request: ResearchRequest):
    """Create the original lightweight deterministic research record."""
    run_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        forecast = get_forecast("cpi_yoy", request.horizon_months, "seasonal_naive", "base")
    except HTTPException:
        forecast = None
    try:
        backtest = get_backtest("cpi_yoy", min(request.horizon_months, 12), 24)
    except HTTPException:
        backtest = None
    observations = load_series("cpi_yoy")
    warnings = ["Research run is a prototype summary; agent orchestration is not connected."]
    retrieved_evidence = []
    evidence_run_id = None
    if request.use_uploaded_evidence:
        if not request.evidence_run_id:
            raise HTTPException(status_code=422, detail="evidence_run_id is required when uploaded evidence is enabled")
        try:
            uuid.UUID(request.evidence_run_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid evidence_run_id format") from exc
        evidence_run_id = request.evidence_run_id
        evidence_response = await get_evidence_service().search(SearchRequest(
            run_id=evidence_run_id, query=request.question, top_k=5,
            evidence_ids=request.evidence_ids,
        ))
        retrieved_evidence = [item.model_dump(mode="json") for item in evidence_response.results]
        warnings.extend(evidence_response.warnings)
        for item in evidence_response.results:
            get_evidence_service().validate_evidence(evidence_run_id, item.evidence_id)

    event_run_id = evidence_run_id or run_id
    emit_event("critic_started", {"run_id": event_run_id, "research_run_id": run_id})
    critic = run_critic(
        planner_output={}, data_output={}, growth_output={}, external_output={},
        econometrics_output={"model": (forecast or {}).get("model", "seasonal_naive"),
                             "forecast": forecast, "backtest": backtest,
                             "scenario_assumptions": [scenario.model_dump() for scenario in request.scenarios]},
        policy_output={}, retrieved_evidence=retrieved_evidence,
    )
    emit_event("critic_completed", {"run_id": event_run_id, "research_run_id": run_id,
                                    "overall_status": critic.overall_status})
    model_evidence = [{"kind": "MODEL FORECAST", "model": (forecast or {}).get("model", "seasonal_naive"),
                       "forecast": forecast, "backtest": backtest}] if forecast is not None else []
    emit_event("report_started", {"run_id": event_run_id, "research_run_id": run_id})
    report = {
        "title": "Research run: " + request.question[:100], "question": request.question,
        "created_at": created_at, "forecast": forecast, "backtest": backtest,
        "scenarios": [scenario.model_dump() for scenario in request.scenarios],
        "assumptions": [], "warnings": warnings,
        "observed_data": [{"series_id": item.series_id, "date": item.date, "value": item.value,
                           "source": item.source, "unit": item.unit} for item in observations[-12:]],
        "model_evidence": model_evidence,
        "document_evidence": retrieved_evidence,
        "critic": critic.model_dump(mode="json"),
        "executive_summary": "Prototype scenario analysis. Not an official RBI recommendation.",
    }
    emit_event("report_completed", {"run_id": event_run_id, "research_run_id": run_id,
                                    "document_evidence_count": len(retrieved_evidence)})
    run = {"run_id": run_id, "status": "completed_with_warnings", "created_at": created_at,
           "question": request.question, "data_vintage": observations[-1].date if observations else None,
           "forecast": forecast, "backtest": backtest, "scenarios": report["scenarios"],
           "evidence_run_id": evidence_run_id, "document_evidence": retrieved_evidence,
           "critic": report["critic"],
           "events": [], "report": report, "warnings": warnings}
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{run_id}.json"
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return run


@router.get("/research/{run_id}")
def get_research_run(run_id: str):
    return _read_run(run_id)


@router.get("/research/{run_id}/events")
def get_research_events(run_id: str):
    run = _read_run(run_id)
    return {"run_id": run_id, "events": run["events"]}


@router.get("/research/{run_id}/stream")
def stream_research_events(run_id: str):
    run = _read_run(run_id)
    return {"run_id": run_id, "status": run["status"], "events": run["events"],
            "streaming": False, "note": "Events are persisted; live event streaming is not implemented."}


@router.get("/reports/{run_id}")
def get_research_report(run_id: str):
    run = _read_run(run_id)
    return {"run_id": run_id, "status": run["status"], "report": run["report"]}
