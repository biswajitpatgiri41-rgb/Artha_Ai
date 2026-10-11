"""Evidence API routes."""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.core.security import EvidenceSecurityValidator
from app.evidence.schemas import (
    EvidenceFormat,
    EvidenceLifecycle,
    EvidenceMetadata,
    EvidenceStatus,
    SearchRequest,
    SearchResponse,
    StructuredJSONResult,
    StructuredTableResult,
    UploadResponse,
)
from app.evidence.service import get_evidence_service
from app.evidence.events import get_events
from app.core.config import get_evidence_limits

router = APIRouter(prefix="/evidence", tags=["evidence"])
class EvidenceListResponse(BaseModel):
    run_id: str
    evidence: list[EvidenceMetadata]


class StructuredTableRequest(BaseModel):
    run_id: str
    evidence_id: str
    operation: str
    sheet: Optional[str] = None
    conditions: Optional[dict] = None
    column: Optional[str] = None
    value: Optional[str] = None
    date_column: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)


class StructuredJSONRequest(BaseModel):
    run_id: str
    evidence_id: str
    operation: str
    path: Optional[str] = None
    search_term: Optional[str] = None


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    run_id: str = Form(...),
    file: UploadFile = File(...),
    lifecycle: EvidenceLifecycle = Form(default=EvidenceLifecycle.TEMPORARY),
):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    max_bytes = get_evidence_limits()["max_upload_mb"] * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the configured {max_bytes // (1024 * 1024)} MB upload limit.")
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")

    ext = Path(file.filename or "").suffix.lower()
    mime_type = {
        ".pdf": "application/pdf",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".json": "application/json",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(ext, "application/octet-stream")

    # Security validation
    validator = EvidenceSecurityValidator()
    file_obj = io.BytesIO(content)
    service = get_evidence_service()
    run_file_count = len(service.list_run_evidence(run_id))
    
    valid, error, details = validator.validate_upload(
        file=file_obj,
        filename=file.filename or "unknown",
        mime_type=mime_type,
        file_size=len(content),
        run_file_count=run_file_count,
    )
    
    if not valid:
        raise HTTPException(status_code=422, detail=error)

    try:
        result = await service.upload_file(run_id, file.filename or "unknown", mime_type, content, lifecycle=lifecycle)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed ({type(e).__name__}). Check server logs.") from e


@router.get("/config")
async def evidence_config():
    limits = get_evidence_limits()
    return {"max_upload_bytes": limits["max_upload_bytes"],
            "max_upload_mb": limits["max_upload_mb"],
            "max_files_per_run": limits["max_files_per_run"],
            "max_pdf_pages": limits["max_pdf_pages"],
            "max_csv_rows": limits["max_csv_rows"],
            "max_xlsx_sheets": limits["max_xlsx_sheets"],
            "max_json_bytes": limits["max_json_bytes"],
            "evidence_retention_hours": limits["evidence_retention_hours"],
            "authentication_enabled": False,
            "privacy_notice": "Local development evidence is scoped by run ID. Authentication and multi-user isolation are not implemented."}


@router.get("/events")
async def evidence_events(run_id: str, after: int = Query(default=0, ge=0)):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")
    return {"events": get_events(run_id, after)}


@router.get("/run/{run_id}", response_model=EvidenceListResponse)
async def list_run_evidence(run_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")
    service = get_evidence_service()
    return EvidenceListResponse(run_id=run_id, evidence=service.list_run_evidence(run_id))


@router.get("/{evidence_id}", response_model=EvidenceMetadata)
async def get_evidence_by_id(evidence_id: str, run_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")
    metadata = get_evidence_service().get_metadata(run_id, evidence_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return metadata


@router.delete("/{evidence_id}")
async def delete_evidence_by_id(evidence_id: str, run_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")
    if not get_evidence_service().delete_evidence(run_id, evidence_id):
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"status": "deleted", "evidence_id": evidence_id}


@router.get("/list/{run_id}", response_model=EvidenceListResponse)
async def list_evidence(run_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    evidence = service.list_run_evidence(run_id)
    return EvidenceListResponse(run_id=run_id, evidence=evidence)


@router.get("/{run_id}/{evidence_id}", response_model=EvidenceMetadata)
async def get_evidence(run_id: str, evidence_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    metadata = service.get_metadata(run_id, evidence_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return metadata


@router.delete("/{run_id}/{evidence_id}")
async def delete_evidence(run_id: str, evidence_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    success = service.delete_evidence(run_id, evidence_id)
    if not success:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"status": "deleted", "evidence_id": evidence_id}


@router.post("/search", response_model=SearchResponse)
async def search_evidence(request: SearchRequest):
    try:
        uuid.UUID(request.run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    return await service.search(request)


@router.post("/validate/{run_id}/{evidence_id}")
async def validate_evidence(run_id: str, evidence_id: str):
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    result = service.validate_evidence(run_id, evidence_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/table/query", response_model=StructuredTableResult)
async def query_structured_table(request: StructuredTableRequest):
    try:
        uuid.UUID(request.run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    try:
        return service.query_table(
            request.run_id,
            request.evidence_id,
            request.operation,
            sheet=request.sheet,
            conditions=request.conditions or {},
            column=request.column,
            value=request.value,
            date_column=request.date_column,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.post("/json/query", response_model=StructuredJSONResult)
async def query_structured_json(request: StructuredJSONRequest):
    try:
        uuid.UUID(request.run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format")

    service = get_evidence_service()
    try:
        return service.query_json(
            request.run_id,
            request.evidence_id,
            request.operation,
            path=request.path,
            search_term=request.search_term,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
