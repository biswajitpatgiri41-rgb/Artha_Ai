"""Copy the project's current runtime data into the linked Supabase project.

Run after `vercel env pull .env.local` from the repository root. The script is
idempotent: macro observations, research runs, evidence objects, and upload
records are upserted by stable identifiers. It does not delete local files.
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import zipfile
import argparse
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.series_registry import SERIES_REGISTRY
from app.db import supabase as db


def _load_environment_file() -> None:
    """Load Vercel-pulled env values without requiring python-dotenv."""
    candidates = [ROOT / ".env.local", ROOT / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip("\"'")
            if key in {"SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"}:
                os.environ.setdefault(key, value)


def _migrate_series() -> tuple[int, int]:
    series_count = observation_count = 0
    for snapshot in sorted((ROOT / "data" / "interim").glob("*_normalized_final.json")):
        series_id = snapshot.name.removesuffix("_normalized_final.json")
        entry = SERIES_REGISTRY.get(series_id)
        if entry is None:
            print(f"Skipped unregistered final series: {series_id}")
            continue
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        observations = payload.get("observations", []) if isinstance(payload, dict) else payload
        if not isinstance(observations, list) or not observations:
            print(f"Skipped empty final snapshot: {snapshot.name}")
            continue
        rows_by_date = {
            item["obs_date"]: {
            "obs_date": item["obs_date"],
            "value": float(item["value"]),
            "unit": item.get("unit") or entry.unit,
            "frequency": entry.frequency.value,
            "source": item.get("source") or entry.preferred_source.value,
            "source_url": item.get("source_url") or entry.source_url,
            "release_date": item.get("release_date"),
            "base_year": item.get("base_year") or entry.base_year,
            "seasonal_adjustment": None,
            "revision_tag": "supplied_final_20261016",
            "retrieved_at": item.get("retrieved_at"),
            }
            for item in observations
            if item.get("obs_date") and item.get("value") is not None
        }
        rows = [rows_by_date[key] for key in sorted(rows_by_date)]
        if not rows:
            print(f"Skipped final snapshot with no valid rows: {snapshot.name}")
            continue
        db.save_macro_observations(series_id, rows, replace=True)
        series_count += 1
        observation_count += len(rows)

    # The trained model bundle carries the official 2024-base CPI YoY target
    # separately from the index snapshots. Store it as its own canonical series.
    archive = ROOT / "notebooks" / "new_datasets.zip"
    target_member = "Artha_AI_Models/artifacts/retrained_20261016_extended/mospi_2024_base_target.csv"
    if archive.is_file():
        import csv
        from io import TextIOWrapper

        entry = SERIES_REGISTRY.get("cpi_yoy")
        if entry is not None:
            with zipfile.ZipFile(archive) as bundle:
                with TextIOWrapper(bundle.open(target_member), encoding="utf-8-sig", newline="") as stream:
                    observations = list(csv.DictReader(stream))
            rows_by_date = {
                f"{row['date']}-01": {
                "obs_date": f"{row['date']}-01",
                "value": float(row["target_yoy"]),
                "unit": "percent",
                "frequency": entry.frequency.value,
                "source": row.get("target_origin") or "MoSPI 2024-base final CPI model dataset",
                "source_url": entry.source_url,
                "release_date": None,
                "base_year": "2024=100",
                "seasonal_adjustment": None,
                "revision_tag": "supplied_final_20261016",
                "retrieved_at": None,
                }
                for row in observations
                if row.get("date") and row.get("target_yoy")
            }
            rows = [rows_by_date[key] for key in sorted(rows_by_date)]
            db.save_macro_observations("cpi_yoy", rows, replace=True)
            series_count += 1
            observation_count += len(rows)
    else:
        print(f"CPI YoY model target not imported; archive not found: {archive}")
    return series_count, observation_count


def _migrate_research_runs() -> int:
    directory = ROOT / "data" / "runs"
    count = 0
    if not directory.is_dir():
        return count
    for path in directory.glob("*.json"):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(run, dict) and run.get("run_id") and run.get("created_at"):
                db.upsert_research_run(run)
                count += 1
        except (OSError, ValueError, KeyError, db.SupabaseRequestError) as exc:
            print(f"Skipped research run {path.name}: {type(exc).__name__}")
    return count


def _migrate_evidence() -> tuple[int, int]:
    from app.evidence.schemas import EvidenceMetadata
    from app.evidence.service import EvidenceService
    from app.evidence.storage import EvidenceStorage

    storage = EvidenceStorage()
    service = EvidenceService()
    document_count = byte_count = 0
    metadata_files = list(storage.base_dir.glob("*/*.meta.json"))
    for metadata_path in metadata_files:
        try:
            metadata = EvidenceMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
            file_path = storage.get_file_path(metadata.run_id, metadata.stored_filename)
            if not file_path.is_file():
                print(f"Skipped missing evidence file for {metadata.evidence_id}")
                continue
            content = file_path.read_bytes()
            key = f"{metadata.run_id}/{metadata.stored_filename}"
            mime = metadata.mime_type or mimetypes.guess_type(metadata.original_filename)[0] or "application/octet-stream"
            db.storage_upload("evidence-files", key, content, mime)
            db.save_evidence_metadata(metadata.model_dump(mode="json"), key)
            # Recreate parsed/indexed content in the durable database vector store.
            service._process_file(metadata.run_id, metadata, file_path)
            document_count += 1
            byte_count += len(content)
        except (OSError, ValueError, db.SupabaseRequestError) as exc:
            print(f"Skipped evidence metadata {metadata_path.name}: {type(exc).__name__}")
    return document_count, byte_count


def _migrate_data_uploads() -> tuple[int, int]:
    directory = ROOT / "data" / "manifests"
    upload_count = byte_count = 0
    if not directory.is_dir():
        return upload_count, byte_count
    for manifest_path in directory.glob("data_upload_*.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            series_id = str(manifest["series_id"])
            uploaded_at = str(manifest["uploaded_at_utc"])
            raw_path_value = Path(str(manifest["raw_file"]))
            raw_path = (ROOT / raw_path_value).resolve()
            raw_path.relative_to(ROOT.resolve())
            object_key = None
            if raw_path.is_file():
                object_key = f"{series_id}/legacy/{manifest_path.stem}/{raw_path.name}"
                mime = mimetypes.guess_type(raw_path.name)[0] or "application/octet-stream"
                content = raw_path.read_bytes()
                db.storage_upload("series-uploads", object_key, content, mime)
                byte_count += len(content)
            db.save_data_upload(manifest_path.stem, series_id, uploaded_at, object_key, manifest)
            upload_count += 1
        except (OSError, ValueError, KeyError, db.SupabaseRequestError) as exc:
            print(f"Skipped upload manifest {manifest_path.name}: {type(exc).__name__}")
    return upload_count, byte_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate runtime data to Supabase.")
    parser.add_argument(
        "--macro-only",
        action="store_true",
        help="Migrate macro observations only; skip optional evidence and upload records.",
    )
    args = parser.parse_args()
    _load_environment_file()
    if not os.getenv("SUPABASE_URL"):
        project_ref_file = ROOT / "supabase" / ".temp" / "project-ref"
        if project_ref_file.is_file():
            project_ref = project_ref_file.read_text(encoding="utf-8").strip()
            if project_ref:
                os.environ["SUPABASE_URL"] = f"https://{project_ref}.supabase.co"
    if not os.getenv("SUPABASE_SECRET_KEY") and not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        os.environ["SUPABASE_SECRET_KEY"] = getpass(
            "Paste the Supabase secret key for this one-time import (input hidden): "
        ).strip()
    if not db.is_configured():
        print("Supabase credentials missing. Run `vercel env pull .env.local` from the repository root first.")
        return 2

    series_count, observation_count = _migrate_series()
    run_count = 0 if args.macro_only else _migrate_research_runs()
    evidence_count, evidence_bytes = (0, 0) if args.macro_only else _migrate_evidence()
    upload_count, upload_bytes = (0, 0) if args.macro_only else _migrate_data_uploads()

    print("Supabase runtime-data migration complete.")
    print(f"Macro series: {series_count}; observations: {observation_count}")
    print(f"Research runs: {run_count}")
    print(f"Evidence files: {evidence_count}; bytes: {evidence_bytes}")
    print(f"Data uploads: {upload_count}; raw-file bytes: {upload_bytes}")
    print("Local originals were retained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
