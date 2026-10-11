"""Evidence processing and RAG module for the Agentic Monetary Policy project.

This module handles:
- File upload and validation
- Format-specific parsing (PDF, CSV, XLSX, JSON, TXT, MD)
- Text extraction and chunking
- Embedding generation via configurable providers
- Vector storage and retrieval
- Structured evidence tools for tabular data
- Evidence lifecycle management (TEMPORARY/SAVED)
- Operational events for live flow visualization
"""

from app.evidence.schemas import (
    EvidenceDocument,
    EvidenceMetadata,
    EvidenceFormat,
    EvidenceStatus,
    EvidenceLifecycle,
    RetrievedEvidence,
    RetrievedEvidenceLocation,
    SearchRequest,
    SearchResponse,
    UploadResponse,
    StructuredTableResult,
    StructuredJSONResult,
)
from app.evidence.storage import EvidenceStorage
from app.evidence.parsers import FormatRouter, parse_file
from app.evidence.chunking import chunk_text, ChunkConfig
from app.evidence.embeddings import EmbeddingProvider, get_embedding_provider
from app.evidence.vector_store import VectorStore, get_vector_store
from app.evidence.retrieval import retrieve_evidence
from app.evidence.service import EvidenceService
from app.evidence.events import (
    emit_evidence_upload_started,
    emit_evidence_uploaded,
    emit_evidence_parsing_started,
    emit_evidence_indexed,
    emit_retrieval_started,
    emit_retrieval_completed,
    emit_evidence_validation_started,
    emit_evidence_validation_completed,
    register_event_callback,
)

__all__ = [
    "EvidenceDocument",
    "EvidenceMetadata",
    "EvidenceFormat",
    "EvidenceStatus",
    "EvidenceLifecycle",
    "RetrievedEvidence",
    "RetrievedEvidenceLocation",
    "SearchRequest",
    "SearchResponse",
    "UploadResponse",
    "StructuredTableResult",
    "StructuredJSONResult",
    "EvidenceStorage",
    "FormatRouter",
    "parse_file",
    "chunk_text",
    "ChunkConfig",
    "EmbeddingProvider",
    "get_embedding_provider",
    "VectorStore",
    "get_vector_store",
    "retrieve_evidence",
    "EvidenceService",
    # Events
    "emit_evidence_upload_started",
    "emit_evidence_uploaded",
    "emit_evidence_parsing_started",
    "emit_evidence_indexed",
    "emit_retrieval_started",
    "emit_retrieval_completed",
    "emit_evidence_validation_started",
    "emit_evidence_validation_completed",
    "register_event_callback",
]