import asyncio
import ipaddress
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router
from .research_routes import router as research_router
from .data_routes import router as data_router
from .evidence_routes import router as evidence_router
from .advanced_routes import router as advanced_router
from .admin_auth_routes import router as admin_auth_router
from .admin_monitoring_routes import router as admin_monitoring_router
from .admin_telemetry import telemetry
from app.tools.research import catalog
from app.core.config import get_settings
from app.models.final_package import final_package_status

settings = get_settings()
logger = logging.getLogger(__name__)


def _client_ip(request) -> str | None:
    """Resolve the socket peer, honoring X-Forwarded-For only from trusted proxies."""
    peer = request.client.host if request.client else None
    trusted = {
        item.strip() for item in os.getenv("TRUSTED_PROXY_IPS", "").split(",")
        if item.strip()
    }
    if not peer or peer not in trusted:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [item.strip() for item in forwarded.split(",") if item.strip()]
    # Walk from the socket peer toward the original client. Ignore trusted
    # proxy hops; the first untrusted address is the best available client IP.
    for candidate in reversed(chain):
        if candidate not in trusted:
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                return peer
    return peer


async def _temporary_evidence_retention_worker():
    while True:
        try:
            from app.evidence.service import get_evidence_service
            await asyncio.to_thread(lambda: get_evidence_service().cleanup_expired_evidence())
        except Exception:
            logger.exception("Temporary evidence retention cleanup failed")
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(_app):
    worker = asyncio.create_task(_temporary_evidence_retention_worker())
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


app = FastAPI(title="Agentic Monetary Policy API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    # The API currently uses no cookie-based authentication. Do not enable
    # credentialed cross-origin requests until a CSRF-protected session exists.
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Filename", "Authorization"],
)
app.include_router(router)
app.include_router(research_router)
app.include_router(data_router)
app.include_router(evidence_router)
app.include_router(advanced_router)
app.include_router(admin_auth_router)
app.include_router(admin_monitoring_router)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, exc: RequestValidationError):
    """Return validation locations/messages without echoing rejected values."""
    errors = [
        {"location": [str(part) for part in item.get("loc", ())],
         "message": item.get("msg", "Invalid value"),
         "type": item.get("type", "validation_error")}
        for item in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.middleware("http")
async def security_headers(request, call_next):
    """Apply browser hardening headers to API responses."""
    started = telemetry.begin()
    status_code = 500
    bytes_out = 0
    try:
        response = await call_next(request)
        status_code = response.status_code
        try:
            body = getattr(response, "body", None)
            bytes_out = len(body) if body is not None else int(response.headers.get("content-length", "0"))
        except ValueError:
            bytes_out = 0
    except Exception:
        raise
    finally:
        try:
            bytes_in = int(request.headers.get("content-length", "0"))
        except ValueError:
            bytes_in = 0
        telemetry.finish(
            started,
            request.method,
            request.url.path,
            status_code,
            max(0, bytes_in),
            max(0, bytes_out),
            _client_ip(request),
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/health")
def health_check():
    """Health check endpoint reporting service status."""
    llm_status = "configured" if settings.is_llm_configured() else "not_configured"
    available_series = sum(1 for item in catalog() if item["available"])
    return {
        "status": "ok",
        "llm": llm_status,
        "data": "available" if available_series else "no_observations",
        "available_series": available_series,
        "econometrics": "baseline_tools_available",
        "final_model_package": final_package_status()["status"],
    }


@app.get("/visitor-heartbeat", include_in_schema=False)
def visitor_heartbeat():
    """Allow an open research page to stay visible between data requests.

    The middleware records only the network address and request metadata; no
    cookies, user identifiers, or request body are collected here.
    """
    return {"status": "ok"}
