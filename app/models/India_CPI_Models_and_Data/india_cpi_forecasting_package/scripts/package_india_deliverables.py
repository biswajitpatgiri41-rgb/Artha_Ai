#!/usr/bin/env python3
"""Build and validate the complete India CPI model/data deliverable ZIP."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "India_CPI_Models_and_Data.zip"
ARCHIVE_PREFIX = "india_cpi_forecasting_package"


def required_files() -> list[Path]:
    paths = [
        ROOT / "README.md",
        ROOT / "requirements.txt",
        ROOT / "source_research_notes.md",
        ROOT / "data/raw/kaggle/kaggle_india_cpi_2013_2023.zip",
        ROOT / "data/raw/kaggle/datafile.csv",
        ROOT / "data/raw/official/All_India_Index_Upto_Aug25.csv",
        ROOT / "data/raw/official/mospi_cpi_december_2025_release.pdf",
        ROOT / "data/raw/official/mospi_cpi_december_2025_release.txt",
        ROOT / "data/raw/official/mospi_cpi_january_2026_release.pdf",
        ROOT / "data/raw/official/mospi_cpi_january_2026_release.txt",
        ROOT / "data/processed/india_cpi_observations_long.csv",
        ROOT / "data/processed/india_cpi_monthly_panel.csv",
        ROOT / "data/processed/india_headline_cpi_target.csv",
        ROOT / "data/processed/source_manifest.json",
        ROOT / "data/processed/normalization_report.json",
        ROOT / "models/model_artifact_manifest.json",
        ROOT / "reports/metrics_by_model_horizon.csv",
        ROOT / "reports/threshold_scorecard.csv",
        ROOT / "reports/rolling_origin_forecasts.csv",
        ROOT / "reports/training_config.json",
        ROOT / "reports/model_selection.json",
        ROOT / "reports/evaluation_summary.md",
        ROOT / "reports/artifact_validation.json",
        ROOT / "reports/archived_2012_base_forecasts.csv",
    ]
    paths.extend(sorted((ROOT / "models").glob("*.pkl")))
    paths.extend(sorted((ROOT / "scripts").glob("*.py")))
    paths.extend(sorted((ROOT / "reports").glob("*.csv")))
    paths.extend(sorted((ROOT / "reports").glob("*.json")))
    paths.extend(sorted((ROOT / "reports").glob("*.md")))
    # Remove duplicates while preserving order; only ordinary project files are included.
    unique: list[Path] = []
    seen = set()
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = required_files()
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required deliverables are missing:\n" + "\n".join(missing))

    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{ARCHIVE_PREFIX}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"ZIP integrity check failed on {bad_member}")
        names = set(archive.namelist())
        required_names = {
            f"{ARCHIVE_PREFIX}/README.md",
            f"{ARCHIVE_PREFIX}/models/best_trained_model.pkl",
            f"{ARCHIVE_PREFIX}/data/processed/india_cpi_monthly_panel.csv",
            f"{ARCHIVE_PREFIX}/reports/threshold_scorecard.csv",
            f"{ARCHIVE_PREFIX}/reports/evaluation_summary.md",
        }
        missing_members = sorted(required_names - names)
        if missing_members:
            raise RuntimeError(f"ZIP is missing required members: {missing_members}")

    zip_hash = file_sha256(ZIP_PATH)
    checksum_path = ZIP_PATH.with_suffix(ZIP_PATH.suffix + ".sha256")
    checksum_path.write_text(f"{zip_hash}  {ZIP_PATH.name}\n", encoding="utf-8")
    result = {
        "zip_path": str(ZIP_PATH),
        "zip_bytes": ZIP_PATH.stat().st_size,
        "zip_sha256": zip_hash,
        "sha256_sidecar": str(checksum_path),
        "files_included": len(files),
        "pickle_model_count": len(list((ROOT / "models").glob("*.pkl"))),
        "zip_integrity": "PASS",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
