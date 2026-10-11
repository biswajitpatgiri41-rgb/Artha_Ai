from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.core.series_registry import SERIES_REGISTRY
from app.tools.research import INTERIM, ROOT, load_series

router = APIRouter(prefix="/data", tags=["data management"])
RAW = ROOT / "data" / "raw"
MANIFESTS = ROOT / "data" / "manifests"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_UPLOAD_ROWS = 200_000
MAX_UPLOAD_COLUMNS = 100
MAX_XLSX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
DEMO_REPO_FILE = ROOT / "data" / "demo" / "synthetic_repo_rate_preview.csv"
MONTHLY_IDS = {"cpi_headline", "food_inflation", "iip", "us_cpi", "us_policy_rate", "wpi"}
ANNUAL_IDS = {"india_cpi_inflation_annual_wb", "india_gdp_growth_annual_wb", "world_gdp_growth_annual_wb"}

# Inputs that participate in the target/model; other registered series are
# accepted as optional inputs so later feature expansion does not need a new UI.
CORE_IDS = ["cpi_headline", "food_inflation", "iip", "repo_rate", "brent_crude", "inr_usd"]
OPTIONAL_IDS = ["wpi", "bank_credit", "m3", "us_cpi", "us_policy_rate", "rainfall_deviation",
                "india_cpi_inflation_annual_wb", "india_gdp_growth_annual_wb", "world_gdp_growth_annual_wb"]
DISPLAY = {
    "cpi_headline": ("Headline CPI index", "MoSPI", "Monthly index; keep one consistent base series."),
    "food_inflation": ("Food CPI index", "MoSPI", "Monthly food index; importer derives year-over-year inflation."),
    "iip": ("IIP general index", "MoSPI", "Monthly index; use the 2022-23 base series or provide its base_year column. Do not splice old/new bases without an official link."),
    "repo_rate": ("Policy repo rate", "RBI", "Effective-date observations; values in percent per annum."),
    "brent_crude": ("Brent crude price", "EIA / FRED", "Daily or monthly price in USD per barrel."),
    "inr_usd": ("INR per USD", "FRED / RBI", "Daily or monthly exchange rate."),
    "wpi": ("Wholesale price index", "MoSPI", "Optional monthly index; record its base year."),
    "bank_credit": ("Scheduled-bank credit", "RBI", "Optional; frequency and unit must match the source export."),
    "m3": ("Broad money M3", "RBI", "Optional; frequency and unit must match the source export."),
    "us_cpi": ("US CPI index", "FRED", "Optional monthly external context."),
    "us_policy_rate": ("US policy rate", "FRED", "Optional monthly external context."),
    "rainfall_deviation": ("Rainfall deviation", "IMD", "Optional; annual or monthly series as documented by source."),
    "india_cpi_inflation_annual_wb": ("India CPI inflation (annual)", "World Bank", "Context only; do not interpolate into monthly training data."),
    "india_gdp_growth_annual_wb": ("India GDP growth (annual)", "World Bank", "Context only; do not interpolate into monthly training data."),
    "world_gdp_growth_annual_wb": ("World GDP growth (annual)", "World Bank", "Context only; do not interpolate into monthly training data."),
}


def _latest_snapshot(series_id: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for path in sorted(INTERIM.glob(f"{series_id}_normalized_*.json"), key=lambda p: p.stat().st_mtime):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            observations = payload.get("observations", []) if isinstance(payload, dict) else payload
            if isinstance(payload, dict) and payload.get("mode") == "replace":
                latest.clear()
            for row in observations:
                day = str(row.get("obs_date", ""))[:10]
                if day:
                    latest[day] = row
        except (OSError, ValueError, TypeError):
            continue
    return latest


def _file_to_frame(filename: str, content: bytes) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            from io import BytesIO
            if b"\x00" in content[:4096]:
                raise HTTPException(status_code=415, detail="CSV upload contains binary content.")
            frame = pd.read_csv(BytesIO(content), nrows=MAX_UPLOAD_ROWS + 1, encoding="utf-8-sig")
        elif suffix in {".xlsx", ".xlsm"}:
            from io import BytesIO
            if not content.startswith(b"PK"):
                raise HTTPException(status_code=415, detail="Excel file signature is invalid.")
            with zipfile.ZipFile(BytesIO(content)) as archive:
                members = archive.infolist()
                expanded_bytes = sum(member.file_size for member in members)
                if len(members) > 10_000 or expanded_bytes > MAX_XLSX_UNCOMPRESSED_BYTES:
                    raise HTTPException(status_code=413, detail="Excel workbook expands beyond the allowed processing limit.")
                if any(member.file_size > 0 and member.file_size / max(member.compress_size, 1) > 1000 for member in members):
                    raise HTTPException(status_code=413, detail="Excel workbook compression ratio exceeds the allowed limit.")
            frame = pd.read_excel(BytesIO(content), nrows=MAX_UPLOAD_ROWS + 1, engine="openpyxl")
        else:
            raise HTTPException(status_code=415, detail="Upload a CSV or .xlsx/.xlsm workbook.")
    except HTTPException:
        raise
    except Exception as exc:
        # Parser errors may contain local paths or workbook internals. Keep
        # the detailed exception in server-side logs only.
        import logging
        logging.getLogger(__name__).warning("Rejected upload during parsing (%s)", type(exc).__name__)
        raise HTTPException(status_code=422, detail="Could not parse uploaded file. Check that it is a valid CSV or Excel workbook.") from exc
    if frame.empty:
        raise HTTPException(status_code=422, detail="The uploaded file has no data rows.")
    if len(frame) > MAX_UPLOAD_ROWS:
        raise HTTPException(status_code=413, detail=f"Upload exceeds the {MAX_UPLOAD_ROWS} row limit.")
    if len(frame.columns) > MAX_UPLOAD_COLUMNS:
        raise HTTPException(status_code=413, detail=f"Upload exceeds the {MAX_UPLOAD_COLUMNS} column limit.")
    return frame


def _column(frame: pd.DataFrame, candidates: set[str]) -> str | None:
    normalized = {re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_"): col for col in frame.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _validate_value(series_id: str, value: float) -> None:
    bounds = {
        "cpi_headline": (0, 100000), "food_inflation": (0, 100000), "iip": (0, 100000),
        "repo_rate": (0, 30), "brent_crude": (0, 1000), "inr_usd": (0, 10000),
        "wpi": (0, 100000), "bank_credit": (0, 1e15), "m3": (0, 1e15),
        "us_cpi": (0, 100000), "us_policy_rate": (0, 30), "rainfall_deviation": (-100, 500),
    }
    low, high = bounds.get(series_id, (-1e15, 1e15))
    if not low <= value <= high:
        raise HTTPException(status_code=422, detail=f"Value {value} is outside the accepted range for {series_id} ({low}, {high}).")


@router.get("/requirements")
def get_data_requirements():
    sections = []
    for ids, required in ((CORE_IDS, True), (OPTIONAL_IDS, False)):
        for series_id in ids:
            entry = SERIES_REGISTRY[series_id]
            rows = load_series(series_id)
            labels = DISPLAY[series_id]
            sections.append({
                "id": series_id, "name": labels[0], "source": labels[1], "notes": labels[2],
                "required_for_mvp": required, "frequency": entry.frequency.value, "unit": entry.unit,
                "base_year": entry.base_year, "available": len(rows) > 0,
                "observation_count": len(rows), "start_date": rows[0].date if rows else None,
                "end_date": rows[-1].date if rows else None,
                "minimum_months": 60 if required else None,
            })
    headline = load_series("cpi_headline")
    by_month = {pd.Period(item.date, freq="M"): item.value for item in headline}
    target_months = [month for month in by_month if month - 12 in by_month]
    return {"readiness": {"headline_index_months": len(headline), "derived_yoy_months": len(target_months),
                          "minimum_training_months": 60,
                          "status": "not_ready" if len(target_months) < 60 else "ready_for_initial_training"},
            "upload_schema": {"required_columns": ["date", "value"],
                              "optional_columns": ["release_date", "source", "unit", "base_year", "seasonal_adjustment", "revision_tag"],
                              "date_format": "YYYY-MM-DD", "max_file_bytes": MAX_UPLOAD_BYTES,
                              "update_mode": "upsert (new observations add; matching dates update)"},
            "sections": sections}


@router.get("/demo/repo-rate")
def download_demo_repo_rate():
    if not DEMO_REPO_FILE.is_file():
        raise HTTPException(status_code=404, detail="No simulated demo series is installed.")
    return FileResponse(DEMO_REPO_FILE, media_type="text/csv", filename="synthetic_repo_rate_preview.csv")


@router.post("/upload/{series_id}")
async def upload_series(series_id: str, request: Request,
                        mode: str = Query(default="upsert", pattern="^(upsert|replace)$")):
    if series_id not in CORE_IDS + OPTIONAL_IDS:
        raise HTTPException(status_code=404, detail="This series is not enabled for uploads.")
    filename = Path(request.headers.get("x-filename", "upload.csv")).name
    if len(filename) > 255:
        raise HTTPException(status_code=422, detail="Filename is too long.")
    if Path(filename).suffix.lower() not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(status_code=415, detail="Upload a CSV or .xlsx/.xlsm workbook.")
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header.") from exc
    chunks: list[bytes] = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    frame = _file_to_frame(filename, content)
    date_col = _column(frame, {"date", "obs_date", "time_period", "effective_date", "observation_date"})
    value_candidates = {"value", "obs_value", "observation", series_id}
    if series_id == "repo_rate":
        value_candidates.update({"repo", "policy_repo_rate", "policy_laf_repo_rate", "repo_rate_percent"})
    value_col = _column(frame, value_candidates)
    if date_col is None or value_col is None:
        raise HTTPException(status_code=422, detail="File needs date and value columns (or date and a column named after the selected series).")

    dates = pd.to_datetime(frame[date_col], errors="coerce", dayfirst=True)
    values = pd.to_numeric(frame[value_col], errors="coerce")
    bad = dates.isna() | values.isna()
    if bad.any():
        raise HTTPException(status_code=422, detail=f"{int(bad.sum())} row(s) have an invalid date or non-numeric value.")
    parsed = pd.DataFrame({"obs_date": dates.dt.strftime("%Y-%m-%d"), "value": values.astype(float)})
    if parsed["obs_date"].duplicated().any():
        examples = parsed.loc[parsed["obs_date"].duplicated(keep=False), "obs_date"].head(5).tolist()
        raise HTTPException(status_code=422, detail=f"Duplicate dates in upload: {examples}")
    if series_id in MONTHLY_IDS and parsed["obs_date"].str[:7].duplicated().any():
        raise HTTPException(status_code=422, detail="This series is monthly; upload no more than one observation per month.")
    if series_id in ANNUAL_IDS and dates.dt.year.duplicated().any():
        raise HTTPException(status_code=422, detail="This context series is annual; upload no more than one observation per year.")
    if not parsed["value"].map(math.isfinite).all():
        raise HTTPException(status_code=422, detail="Values must be finite numeric observations.")
    for value in parsed["value"]:
        _validate_value(series_id, float(value))

    entry = SERIES_REGISTRY[series_id]
    source_col = _column(frame, {"source"})
    release_col = _column(frame, {"release_date"})
    unit_col = _column(frame, {"unit"})
    base_col = _column(frame, {"base_year"})
    seasonal_col = _column(frame, {"seasonal_adjustment"})
    revision_col = _column(frame, {"revision_tag"})
    if base_col:
        bases = {str(value).strip() for value in frame[base_col].dropna() if str(value).strip()}
        if len(bases) > 1:
            raise HTTPException(status_code=422, detail="The upload mixes multiple base years. Split it into consistent files and verify any linked series before combining.")
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d_%H%M%S_%f")
    source_dir = RAW / entry.preferred_source.value.lower()
    source_dir.mkdir(parents=True, exist_ok=True)
    original_path = source_dir / f"upload_{series_id}_{stamp}{Path(filename).suffix.lower()}"
    original_path.write_bytes(content)

    previous = {} if mode == "replace" else _latest_snapshot(series_id)
    for idx, item in parsed.iterrows():
        row = frame.iloc[idx]
        obs_date = item["obs_date"]
        previous[obs_date] = {
            "obs_date": obs_date, "series_id": series_id, "value": float(item["value"]),
            "unit": str(row[unit_col]) if unit_col and pd.notna(row[unit_col]) else entry.unit,
            "frequency": entry.frequency.value, "source": str(row[source_col]) if source_col and pd.notna(row[source_col]) else entry.preferred_source.value,
            "source_url": entry.source_url, "release_date": str(row[release_col])[:10] if release_col and pd.notna(row[release_col]) else None,
            "base_year": str(row[base_col]) if base_col and pd.notna(row[base_col]) else entry.base_year,
            "seasonal_adjustment": str(row[seasonal_col]) if seasonal_col and pd.notna(row[seasonal_col]) else None,
            "revision_tag": str(row[revision_col]) if revision_col and pd.notna(row[revision_col]) else "uploaded",
            "retrieved_at": now.isoformat(),
        }
    observations = [previous[key] for key in sorted(previous)]
    interim_path = INTERIM / f"{series_id}_normalized_upload_{stamp}.json"
    INTERIM.mkdir(parents=True, exist_ok=True)
    interim_path.write_text(json.dumps({"mode": mode, "observations": observations}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "series_id": series_id, "original_filename": filename, "raw_file": str(original_path.relative_to(ROOT)),
        "sha256": hashlib.sha256(content).hexdigest(), "source": entry.preferred_source.value,
        "source_url": entry.source_url, "uploaded_at_utc": now.isoformat(), "mode": mode,
        "uploaded_observations": len(parsed), "canonical_observations": len(observations),
        "start_date": observations[0]["obs_date"], "end_date": observations[-1]["obs_date"],
        "transformation": "Date/value normalization only; source values retained. Upsert replaces matching dates when mode=upsert.",
    }
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFESTS / f"data_upload_{series_id}_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "uploaded", "series_id": series_id, "mode": mode,
            "uploaded_observations": len(parsed), "total_observations": len(observations),
            "start_date": observations[0]["obs_date"], "end_date": observations[-1]["obs_date"],
            "raw_file": manifest["raw_file"], "manifest": str(manifest_path.relative_to(ROOT))}
