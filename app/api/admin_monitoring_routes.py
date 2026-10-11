"""Read-only process health and traffic endpoints for the admin dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.admin_telemetry import telemetry
from app.core.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin-monitoring"])


@router.get("/metrics")
def admin_metrics():
    snapshot = telemetry.snapshot()
    return {"data": snapshot["metrics"], "request_count_60s": snapshot["request_count_60s"]}


@router.get("/health")
def admin_health():
    checked_at = datetime.now(timezone.utc).isoformat()
    settings = get_settings()
    services = [{
        "name": "FastAPI",
        "status": "healthy",
        "latency": None,
        "lastCheck": checked_at,
        "details": "API process is responding",
    }]
    if settings.is_llm_configured():
        services.append({
            "name": "NVIDIA LLM configuration",
            "status": "unknown",
            "latency": None,
            "lastCheck": checked_at,
            "details": "Credentials and endpoint configured; upstream reachability is not probed",
        })
    else:
        services.append({
            "name": "NVIDIA LLM configuration",
            "status": "unknown",
            "latency": None,
            "lastCheck": checked_at,
            "details": "Not configured",
        })
    return {"deployed": True, "services": services, "checked_at": checked_at}


@router.get("/activity")
def admin_activity():
    return {"data": telemetry.snapshot()["activity"]}


@router.get("/visitors")
def admin_active_visitors():
    """List IP addresses seen calling the API within the active visitor window."""
    return telemetry.active_visitors()
