"""Small server-side Supabase REST/Storage adapter using the existing HTTPX dependency."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import httpx


class SupabaseNotConfigured(RuntimeError):
    pass


class SupabaseRequestError(RuntimeError):
    pass


def credentials() -> tuple[str, str] | None:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return (url, key) if url and key else None


def is_configured() -> bool:
    return credentials() is not None


def _request(method: str, path: str, *, params: dict[str, str] | None = None,
             json_body: Any = None, content: bytes | None = None,
             content_type: str | None = None, headers: dict[str, str] | None = None,
             timeout: float = 20.0) -> httpx.Response:
    config = credentials()
    if not config:
        raise SupabaseNotConfigured("Supabase server credentials are not configured")
    base_url, key = config
    request_headers = {"apikey": key}
    # The new sb_secret keys are API keys, not JWTs; only legacy service_role
    # JWT keys belong in Authorization as a bearer token.
    if not key.startswith("sb_"):
        request_headers["Authorization"] = f"Bearer {key}"
    if not key.startswith("sb_"):
        request_headers["Authorization"] = "Bearer " + key
    if content_type:
        request_headers["Content-Type"] = content_type
    if headers:
        request_headers.update(headers)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method, f"{base_url}/{path.lstrip('/')}", params=params,
                json=json_body, content=content, headers=request_headers,
            )
        response.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        response = getattr(exc, "response", None)
        detail = ""
        if response is not None:
            try:
                detail = response.text[:500].replace("\n", " ")
            except Exception:
                detail = ""
        suffix = f": {detail}" if detail else ""
        raise SupabaseRequestError(
            f"Supabase request failed{f' (HTTP {status})' if status else ''}{suffix}"
        ) from exc


def _response_json(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise SupabaseRequestError("Supabase returned invalid JSON") from exc


def list_rows(table: str, *, select: str, filters: dict[str, str] | None = None,
              order: str | None = None, page_size: int = 1000) -> list[dict[str, Any]]:
    """Read a table in bounded PostgREST pages (avoids its default row cap)."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "select": select,
            "limit": str(page_size),
            "offset": str(offset),
            **(filters or {}),
        }
        if order:
            params["order"] = order
        try:
            response = _request(
                "GET", f"rest/v1/{table}", params=params,
            )
        except SupabaseRequestError as exc:
            # PostgREST returns 416 when the next requested range starts
            # immediately after the final full page.
            if offset and "HTTP 416" in str(exc):
                return rows
            raise
        batch = _response_json(response) or []
        if not isinstance(batch, list):
            raise SupabaseRequestError(f"Unexpected response when reading {table}")
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        offset += page_size


def upsert_rows(table: str, rows: list[dict[str, Any]], conflict: str) -> None:
    if not rows:
        return
    _request("POST", f"rest/v1/{table}", params={"on_conflict": conflict},
             json_body=rows, content_type="application/json",
             headers={"Prefer": "resolution=merge-duplicates,return=minimal"}, timeout=60.0)


def delete_rows(table: str, filters: dict[str, str]) -> None:
    _request("DELETE", f"rest/v1/{table}", params=filters, timeout=30.0)


@lru_cache(maxsize=64)
def _cached_series(series_id: str, cache_bucket: int) -> tuple[dict[str, Any], ...]:
    del cache_bucket  # A changing time bucket invalidates the cache every 30 seconds.
    rows = list_rows(
        "macro_observations", select="*", filters={"series_id": f"eq.{series_id}"},
        order="obs_date.asc",
    )
    return tuple(rows)


def get_macro_observations(series_id: str) -> list[dict[str, Any]] | None:
    if not is_configured():
        return None
    bucket = int(datetime.now(timezone.utc).timestamp() // 30)
    return [dict(row) for row in _cached_series(series_id, bucket)]


def clear_series_cache() -> None:
    _cached_series.cache_clear()


def save_macro_observations(series_id: str, observations: list[dict[str, Any]], *, replace: bool = False) -> int:
    response = _request(
        "POST", "rest/v1/rpc/save_macro_observations",
        json_body={"p_series_id": series_id, "p_observations": observations, "p_replace": replace},
        content_type="application/json",
    )
    clear_series_cache()
    value = _response_json(response)
    return int(value or 0)


def upsert_research_run(run: dict[str, Any]) -> None:
    payload = {
        "run_id": run["run_id"], "created_at": run["created_at"],
        "status": run.get("status", "completed"), "payload": run,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _request("POST", "rest/v1/research_runs", params={"on_conflict": "run_id"},
             json_body=[payload], content_type="application/json",
             headers={"Prefer": "resolution=merge-duplicates,return=minimal"})


def get_research_run(run_id: str) -> dict[str, Any] | None:
    rows = list_rows("research_runs", select="payload",
                     filters={"run_id": f"eq.{run_id}"}, page_size=1)
    return rows[0].get("payload") if rows else None


def list_research_runs(limit: int = 20) -> list[dict[str, Any]]:
    rows = list_rows("research_runs", select="payload", order="created_at.desc",
                     page_size=min(max(limit, 1), 100))
    return [row["payload"] for row in rows[:limit] if isinstance(row.get("payload"), dict)]


def save_evidence_metadata(metadata: dict[str, Any], object_key: str) -> None:
    payload = {
        "evidence_id": metadata["evidence_id"], "run_id": metadata["run_id"],
        "uploaded_at": metadata["uploaded_at"], "object_key": object_key,
        "metadata": metadata, "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _request("POST", "rest/v1/evidence_documents", params={"on_conflict": "evidence_id"},
             json_body=[payload], content_type="application/json",
             headers={"Prefer": "resolution=merge-duplicates,return=minimal"})


def get_evidence_metadata(run_id: str, evidence_id: str) -> dict[str, Any] | None:
    rows = list_rows("evidence_documents", select="metadata",
                     filters={"run_id": f"eq.{run_id}", "evidence_id": f"eq.{evidence_id}"},
                     page_size=1)
    return rows[0].get("metadata") if rows else None


def list_evidence_metadata(run_id: str | None = None) -> list[dict[str, Any]]:
    filters = {"run_id": f"eq.{run_id}"} if run_id else None
    rows = list_rows("evidence_documents", select="metadata", filters=filters,
                     order="uploaded_at.asc")
    return [row["metadata"] for row in rows if isinstance(row.get("metadata"), dict)]


def delete_evidence_metadata(run_id: str, evidence_id: str) -> None:
    _request("DELETE", "rest/v1/evidence_documents",
             params={"run_id": f"eq.{run_id}", "evidence_id": f"eq.{evidence_id}"})


def save_data_upload(upload_id: str, series_id: str, uploaded_at: str,
                     object_key: str | None, manifest: dict[str, Any]) -> None:
    payload = {"upload_id": upload_id, "series_id": series_id,
               "uploaded_at": uploaded_at, "object_key": object_key,
               "manifest": manifest}
    _request("POST", "rest/v1/data_uploads", params={"on_conflict": "upload_id"},
             json_body=[payload], content_type="application/json",
             headers={"Prefer": "resolution=merge-duplicates,return=minimal"})


def storage_upload(bucket: str, object_key: str, content: bytes, content_type: str) -> None:
    quoted_key = quote(object_key, safe="/")
    _request("POST", f"storage/v1/object/{bucket}/{quoted_key}", content=content,
             content_type=content_type,
             headers={"x-upsert": "true"}, timeout=60.0)


def storage_download(bucket: str, object_key: str) -> bytes:
    quoted_key = quote(object_key, safe="/")
    response = _request("GET", f"storage/v1/object/{bucket}/{quoted_key}", timeout=60.0)
    return response.content


def storage_delete(bucket: str, object_key: str) -> None:
    _request("DELETE", f"storage/v1/object/{bucket}",
             json_body={"prefixes": [object_key]},
             content_type="application/json", timeout=30.0)


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def json_safe(value: Any) -> Any:
    """Return a JSON-safe copy for Pydantic/date-backed metadata."""
    return json.loads(json.dumps(value, default=lambda item: item.isoformat()
                                 if hasattr(item, "isoformat") else str(item)))
