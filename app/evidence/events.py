"""Operational events for the Evidence/RAG system.

These events are emitted during evidence processing and can be consumed
by the frontend architecture live flow for visualization.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict
from functools import wraps


# Event callbacks - can be overridden by frontend integration
_event_callbacks: Dict[str, list] = {}
_event_history: deque[dict] = deque(maxlen=2000)
_event_lock = threading.Lock()
_event_sequence = 0


def register_event_callback(event_type: str, callback):
    """Register a callback for a specific event type."""
    if event_type not in _event_callbacks:
        _event_callbacks[event_type] = []
    _event_callbacks[event_type].append(callback)


def emit_event(event_type: str, data: Dict[str, Any]):
    """Emit an event to all registered callbacks."""
    global _event_sequence
    with _event_lock:
        _event_sequence += 1
        event = {
            "id": _event_sequence,
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        _event_history.append(event)
    if event_type in _event_callbacks:
        for callback in _event_callbacks[event_type]:
            try:
                callback(event)
            except Exception:
                # Silently ignore callback errors to not break the main flow
                pass


def get_events(run_id: str, after: int = 0) -> list[dict]:
    """Return recent operational events for one local run only."""
    with _event_lock:
        return [
            event.copy()
            for event in _event_history
            if event["id"] > after and event["data"].get("run_id") == run_id
        ]


# Evidence upload events
def emit_evidence_upload_started(run_id: str, filename: str, size: int, lifecycle: str):
    """Emit when evidence upload starts."""
    emit_event("evidence_upload_started", {
        "run_id": run_id,
        "filename": filename,
        "size": size,
        "lifecycle": lifecycle,
    })


def emit_evidence_uploaded(run_id: str, evidence_id: str, filename: str, format: str, size: int, lifecycle: str):
    """Emit when evidence upload completes."""
    emit_event("evidence_uploaded", {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "filename": filename,
        "format": format,
        "size": size,
        "lifecycle": lifecycle,
    })


def emit_evidence_deleted(run_id: str, evidence_id: str, lifecycle: str):
    emit_event("evidence_deleted", {"run_id": run_id, "evidence_id": evidence_id, "lifecycle": lifecycle})


# Evidence parsing events
def emit_evidence_parsing_started(run_id: str, evidence_id: str, format: str):
    """Emit when evidence parsing starts."""
    emit_event("evidence_parsing_started", {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "format": format,
    })


def emit_evidence_parsing_completed(run_id: str, evidence_id: str, format: str, warning_count: int):
    """Emit when the selected format parser has normalized a document."""
    emit_event("evidence_parsing_completed", {
        "run_id": run_id, "evidence_id": evidence_id, "format": format,
        "warning_count": warning_count,
    })


def emit_evidence_processing_failed(run_id: str, evidence_id: str, format: str, error_type: str):
    """Emit a safe processing failure summary without exposing paths or content."""
    emit_event("evidence_processing_failed", {
        "run_id": run_id, "evidence_id": evidence_id, "format": format,
        "error_type": error_type,
    })


def emit_evidence_ready(run_id: str, evidence_id: str, format: str, chunk_count: int):
    """Emit when parsing/indexing is complete and evidence can be selected."""
    emit_event("evidence_ready", {
        "run_id": run_id, "evidence_id": evidence_id, "format": format,
        "chunk_count": chunk_count,
    })


# Evidence indexing events
def emit_evidence_indexed(run_id: str, evidence_id: str, chunk_count: int, format: str):
    """Emit when evidence chunks are indexed into vector store."""
    emit_event("evidence_indexed", {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "chunk_count": chunk_count,
        "format": format,
    })


# Retrieval events
def emit_retrieval_started(run_id: str, query: str, top_k: int):
    """Emit when evidence retrieval starts."""
    emit_event("retrieval_started", {
        "run_id": run_id,
        "query": query,
        "top_k": top_k,
    })


def emit_retrieval_completed(run_id: str, query: str, result_count: int, top_k: int):
    """Emit when evidence retrieval completes."""
    emit_event("retrieval_completed", {
        "run_id": run_id,
        "query": query,
        "result_count": result_count,
        "top_k": top_k,
    })


# Evidence validation events
def emit_evidence_validation_started(run_id: str, evidence_id: str, format: str):
    """Emit when evidence validation starts."""
    emit_event("evidence_validation_started", {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "format": format,
    })


def emit_evidence_validation_completed(run_id: str, evidence_id: str, valid: bool, checks: Dict[str, bool]):
    """Emit when evidence validation completes."""
    emit_event("evidence_validation_completed", {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "valid": valid,
        "checks": checks,
    })


# Decorator for automatic event emission
def with_events(event_type: str, extract_data_func=None):
    """Decorator to automatically emit events around a function."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract data for started event
            started_data = extract_data_func(*args, **kwargs) if extract_data_func else {}
            emit_event(f"{event_type}_started", started_data)
            
            try:
                result = await func(*args, **kwargs)
                completed_data = {**started_data, "result": result} if extract_data_func else {"result": result}
                emit_event(f"{event_type}_completed", completed_data)
                return result
            except Exception as e:
                emit_event(f"{event_type}_failed", {**started_data, "error": str(e)})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            started_data = extract_data_func(*args, **kwargs) if extract_data_func else {}
            emit_event(f"{event_type}_started", started_data)
            
            try:
                result = func(*args, **kwargs)
                completed_data = {**started_data, "result": result} if extract_data_func else {"result": result}
                emit_event(f"{event_type}_completed", completed_data)
                return result
            except Exception as e:
                emit_event(f"{event_type}_failed", {**started_data, "error": str(e)})
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
