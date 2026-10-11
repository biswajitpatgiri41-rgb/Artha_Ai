"""Additive endpoints for advanced UI modules; unavailable models return empty states."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from app.api.advanced_schemas import DataQualityOutput, ModelRegistryOutput, RegimeOutput
from app.models.final_package import ModelPackageIntegrityError, final_model_registry_records
from app.tools.research import ROOT, catalog

router = APIRouter(tags=["advanced research"])


@router.get("/regimes", response_model=RegimeOutput)
def get_regimes() -> RegimeOutput:
    return RegimeOutput(status="model_integration_pending", regimes=[], warnings=[
        "Regime model integration pending. No historical regime dates or probabilities are available.",
    ])


@router.get("/models/registry", response_model=ModelRegistryOutput)
def get_model_registry() -> ModelRegistryOutput:
    try:
        records = final_model_registry_records()
    except FileNotFoundError:
        return ModelRegistryOutput(status="empty", models=[], warnings=[
            "No registered model available. The final model package is not installed.",
        ])
    except (ModelPackageIntegrityError, OSError, ValueError, KeyError) as exc:
        return ModelRegistryOutput(status="invalid", models=[], warnings=[
            f"Final model artifacts failed integrity or metadata validation: {exc}",
        ])
    return ModelRegistryOutput(status="candidate_artifacts", models=records, warnings=[
        "Imported final-package models are CANDIDATE artifacts only; no model is promoted automatically.",
        "Backtest metrics come from a comparison period used for feature selection, not an untouched final holdout.",
        "The API verifies artifact hashes but does not deserialize joblib files or perform live inference.",
    ])


@router.get("/data-quality", response_model=DataQualityOutput)
def get_data_quality() -> DataQualityOutput:
    """Summarize catalog and the latest real ingestion manifest for each series."""
    today = date.today()
    rows = []
    for item in catalog():
        latest = item.get("latest") or {}
        manifest_files = list((ROOT / "data" / "manifests").glob(f"manifest_{item['id']}_*.json"))
        manifest = None
        if manifest_files:
            manifest_path = max(manifest_files, key=lambda path: path.stat().st_mtime)
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = payload if isinstance(payload, dict) else None
            except (OSError, json.JSONDecodeError):
                manifest = {"status": "FAILED", "warnings": ["Latest ingestion manifest could not be read."]}
        last_date = latest.get("date")
        age_days = None
        try:
            age_days = (today - date.fromisoformat(str(last_date)[:10])).days if last_date else None
        except ValueError:
            pass
        enabled = bool(item.get("enabled"))
        available = bool(item.get("available"))
        retrieved_at = (manifest or {}).get("imported_at") or (manifest or {}).get("created_at") or latest.get("retrieved_at")
        release_date = (manifest or {}).get("release_date") or latest.get("release_date")
        manifest_status = str((manifest or {}).get("status", "")).upper()
        retrieval_age = None
        try:
            if retrieved_at:
                retrieval_age = (datetime.now(timezone.utc) - datetime.fromisoformat(str(retrieved_at).replace("Z", "+00:00"))).days
        except (ValueError, TypeError):
            pass
        # Frequency-derived freshness thresholds; not a claim about upstream connectivity.
        threshold = {"M": 62, "Q": 125, "A": 550, "D": 14, "W": 28}.get(item.get("frequency"), 180)
        if not enabled:
            health = "NOT CONFIGURED"
        elif manifest_status and manifest_status not in {"SUCCESS", "COMPLETED", "OK"}:
            health = "FAILED"
        elif not available:
            health = "FAILED"
        elif (age_days is not None and age_days > threshold) or (retrieval_age is not None and retrieval_age > threshold):
            health = "STALE"
        elif retrieved_at and manifest_status in {"SUCCESS", "COMPLETED", "OK"}:
            health = "HEALTHY"
        else:
            health = "WARNING"
        manifest_warnings = (manifest or {}).get("warnings")
        rows.append({
            "series_id": item["id"], "source": item["source"], "health": health,
            "last_observation": last_date, "last_retrieval": retrieved_at,
            "release_date": release_date, "data_vintage": (manifest or {}).get("max_date") or last_date,
            "observation_count": item.get("observation_count", 0), "unit": item.get("unit"),
            "base_year": item.get("base_year"), "validation_issues": manifest_warnings,
            "manifest_status": manifest_status or None,
            "checks": {"missing_observations": None, "duplicates": None,
                       "unit_validation": None, "base_year_consistency": None,
                       "release_freshness": age_days is not None},
            "note": "Catalog-derived local status; upstream health and unavailable validation reports are not inferred.",
        })
    report_paths = [
        ROOT / "data" / "modeling" / "v1" / "validation_report.json",
        ROOT / "data" / "india_macro_dataset_snapshot" / "data" / "manifests" / "data_quality_report.json",
    ]
    reports = []
    for path in report_paths:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                reports.append({"report_id": str(path.relative_to(ROOT)), **payload})
        except (OSError, json.JSONDecodeError):
            reports.append({"report_id": str(path.relative_to(ROOT)), "status": "UNREADABLE"})
    return DataQualityOutput(as_of=datetime.now(timezone.utc), series=rows, validation_reports=reports,
                             warnings=["Local catalog metadata does not verify live provider connectivity."])
