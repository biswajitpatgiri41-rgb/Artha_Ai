"""Pydantic schemas for the Evidence module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceFormat(str, Enum):
    """Supported evidence file formats."""

    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    TXT = "txt"
    MD = "md"


class EvidenceStatus(str, Enum):
    """Processing status for evidence files."""

    UPLOADING = "uploading"
    PARSING = "parsing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class EvidenceLifecycle(str, Enum):
    """Lifecycle state for evidence files."""

    TEMPORARY = "temporary"
    SAVED = "saved"


class EvidenceMetadata(BaseModel):
    """Metadata for an uploaded evidence file."""

    evidence_id: str
    run_id: str
    original_filename: str
    stored_filename: str
    mime_type: str
    size: int
    sha256: str
    uploaded_at: datetime
    format: EvidenceFormat
    status: EvidenceStatus = EvidenceStatus.UPLOADING
    # Lifecycle: temporary (default) or saved
    lifecycle: EvidenceLifecycle = EvidenceLifecycle.TEMPORARY
    # Processing fields
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    indexed_chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    parser_warnings: List[str] = Field(default_factory=list)

    # Structured data metadata (for CSV, XLSX, JSON)
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    data_types: Optional[Dict[str, str]] = None
    sheet_names: Optional[List[str]] = None
    json_schema: Optional[Dict[str, Any]] = None
    top_level_keys: Optional[List[str]] = None


class EvidenceDocument(BaseModel):
    """Normalized document structure after parsing."""

    evidence_id: str
    run_id: str
    format: EvidenceFormat
    filename: str
    # For text-based documents (PDF, TXT, MD)
    text: Optional[str] = None
    pages: Optional[List[Dict[str, Any]]] = None  # page_number, text
    # For structured documents (CSV, XLSX)
    tables: Optional[List[Dict[str, Any]]] = None  # sheet_name, columns, rows, data_types
    # For JSON
    json_data: Any = None
    json_schema: Optional[Dict[str, Any]] = None


class RetrievedEvidenceLocation(BaseModel):
    """Location information for retrieved evidence."""

    # For PDF/TXT/MD
    page: Optional[int] = None
    section: Optional[str] = Field(default=None, max_length=300)
    chunk_id: Optional[str] = Field(default=None, max_length=100)
    # For CSV/XLSX
    rows: Optional[List[int]] = None
    columns: Optional[List[str]] = None
    sheet: Optional[str] = Field(default=None, max_length=255)
    # For JSON
    path: Optional[str] = Field(default=None, max_length=1000)
    keys: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")


class RetrievedEvidence(BaseModel):
    """Retrieved evidence item for critic/report agents."""

    evidence_id: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    format: EvidenceFormat
    location: RetrievedEvidenceLocation
    excerpt: Optional[str] = Field(default=None, max_length=2000)
    structured_result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    retrieval_score: Optional[float] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("structured_result")
    @classmethod
    def limit_structured_result(cls, value):
        if value is not None and len(json.dumps(value, ensure_ascii=True, default=str)) > 10_000:
            raise ValueError("Structured evidence result exceeds the allowed size")
        return value


class SearchRequest(BaseModel):
    """Request for evidence search."""

    run_id: str = Field(min_length=1, max_length=36)
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    evidence_ids: Optional[List[str]] = Field(default=None, max_length=100)


class SearchResponse(BaseModel):
    """Response from evidence search."""

    results: List[RetrievedEvidence] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response from file upload."""

    evidence_id: str
    run_id: str
    filename: str
    format: EvidenceFormat
    size: int
    status: EvidenceStatus
    message: str


class StructuredTableResult(BaseModel):
    """Result from structured table query."""

    source_file: str
    sheet: Optional[str] = None
    rows_involved: List[int]
    columns_involved: List[str]
    data: List[Dict[str, Any]]
    evidence_reference: str


class StructuredJSONResult(BaseModel):
    """Result from structured JSON query."""

    source_file: str
    path: str
    keys_involved: List[str]
    data: Any
    evidence_reference: str


# Configuration for upload - now loaded from settings
# These are defaults; actual values come from get_evidence_limits()
ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".json", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/json",
    "text/plain",
    "text/markdown",
}
# MAX_FILE_SIZE is now dynamic from settings
