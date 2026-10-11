#!/usr/bin/env python
"""Import the RBI DBIE policy-rate export into the project's canonical data.

RBI exposes the historical Key Rates table through the public DBIE download
interface. The current portal does not document a stable public API for this
report, so this script deliberately does not call guessed/private endpoints.
Download the official "Major Monetary Policy Measures – Bank Rate, CRR & SLR"
table as CSV or Excel, save it under data/raw/rbi, then run this script. The
original export is retained unchanged; normalized observations and an audit
manifest are written separately.

Run from the project root:
    python -m scripts.download_rbi_data
    python -m scripts.download_rbi_data --open-portal
    python -m scripts.download_rbi_data --input path/to/export.xlsx
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DBIE_URL = "https://data.rbi.org.in/"
TABLE_TITLE = "Major Monetary Policy Measures – Bank Rate, CRR & SLR"
RAW_DIR = ROOT / "data" / "raw" / "rbi"
INTERIM_DIR = ROOT / "data" / "interim"
MANIFEST_DIR = ROOT / "data" / "manifests"

DATE_LABELS = ("effective date", "date", "from date", "applicable from")
REPO_LABELS = ("policy repo rate", "repo rate", "repo")


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip().lower()


def _read_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        # RBI exports may use UTF-8 with BOM or a Windows encoding.
        try:
            frame = pd.read_csv(path, header=None, encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(path, header=None, encoding="cp1252")
        return [("csv", frame)]
    if suffix in {".xlsx", ".xlsm"}:
        book = pd.ExcelFile(path)
        return [(name, pd.read_excel(book, sheet_name=name, header=None)) for name in book.sheet_names]
    raise ValueError(f"Unsupported export format {suffix!r}; use RBI CSV or .xlsx Excel.")


def _locate_columns(frame: pd.DataFrame) -> tuple[int, int, int] | None:
    """Return header row, date column, and repo column without guessing IDs."""
    for row_index in range(min(40, len(frame))):
        labels = [_clean(value) for value in frame.iloc[row_index].tolist()]
        date_cols = [i for i, label in enumerate(labels) if any(term in label for term in DATE_LABELS)]
        repo_cols = [i for i, label in enumerate(labels) if any(term in label for term in REPO_LABELS)]
        if date_cols and repo_cols:
            # Prefer explicit Policy Repo Rate, then Repo Rate, then Repo.
            repo_cols.sort(key=lambda i: ("policy repo" not in labels[i], "repo rate" not in labels[i]))
            return row_index, date_cols[0], repo_cols[0]
    return None


def _number(value: Any) -> float | None:
    if pd.isna(value) or _clean(value) in {"", "-", "—", "na", "n.a.", "nil"}:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)", str(value).replace(",", ""))
    return float(match.group()) if match else None


def extract_repo_observations(path: Path) -> list[dict[str, Any]]:
    for sheet, frame in _read_tables(path):
        located = _locate_columns(frame)
        if located is None:
            continue
        header_row, date_col, repo_col = located
        rows: list[dict[str, Any]] = []
        for _, row in frame.iloc[header_row + 1 :].iterrows():
            date_value = row.iloc[date_col]
            repo_value = row.iloc[repo_col]
            if pd.isna(date_value) or _number(repo_value) is None:
                continue
            date = pd.to_datetime(date_value, errors="coerce", dayfirst=True)
            value = _number(repo_value)
            if pd.isna(date) or value is None:
                continue
            if not 0 <= value <= 30:
                raise ValueError(f"Unexpected repo rate {value} in {path.name}; expected percent in [0, 30].")
            rows.append({"obs_date": date.date().isoformat(), "value": value, "sheet": sheet})
        if rows:
            return rows
    raise ValueError(
        f"Could not find columns for effective date and policy repo rate in {path.name}. "
        "Export the DBIE Key Rates table with its column headings intact."
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def convert_export(path: Path) -> tuple[Path, Path, dict[str, Any]]:
    observations = extract_repo_observations(path)
    dates = [item["obs_date"] for item in observations]
    if len(dates) != len(set(dates)):
        raise ValueError(f"Duplicate effective dates in {path.name}; resolve in the source export before importing.")
    observations.sort(key=lambda item: item["obs_date"])
    retrieved = datetime.now(timezone.utc)
    rows = [
        {
            "obs_date": item["obs_date"],
            "series_id": "repo_rate",
            "value": item["value"],
            "unit": "percent",
            "frequency": "I",
            "source": "RBI_DBIE",
            "source_url": DBIE_URL,
            "release_date": None,
            "base_year": None,
            "seasonal_adjustment": "not_applicable",
            "revision_tag": "as_downloaded",
            "retrieved_at": retrieved.isoformat(),
        }
        for item in observations
    ]
    stamp = retrieved.strftime("%Y%m%d_%H%M%S_%f")
    interim_path = INTERIM_DIR / f"repo_rate_normalized_{stamp}.json"
    manifest_path = MANIFEST_DIR / f"rbi_repo_rate_import_{stamp}.json"
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    interim_path.write_text(json.dumps({"observations": rows}, indent=2), encoding="utf-8")
    manifest = {
        "variable": "repo_rate",
        "rbi_series": "Policy Repo Rate; event/effective-date observations",
        "rbi_dataset": TABLE_TITLE,
        "source": "Reserve Bank of India, Database on Indian Economy (DBIE)",
        "source_url": DBIE_URL,
        "frequency": "Irregular policy-change dates; monthly panel uses latest rate effective in each month",
        "unit": "percent per annum",
        "start_date": min(dates),
        "end_date": max(dates),
        "observation_count": len(rows),
        "download_timestamp_utc": retrieved.isoformat(),
        "original_file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "original_sha256": sha256(path),
        "transformation": "No value transformation; source rows are represented as canonical effective-date observations.",
        "notes": "The original RBI export is preserved. Monthly resampling carries the last effective policy rate forward; no future values are used.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return interim_path, manifest_path, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Specific RBI DBIE CSV/Excel export to import")
    parser.add_argument("--open-portal", action="store_true", help="Open the official DBIE portal for the documented export")
    args = parser.parse_args()

    if args.open_portal:
        webbrowser.open(DBIE_URL)
        print("In DBIE choose Statistics → Financial Sector → Key Rates →")
        print(f"{TABLE_TITLE}; export CSV/Excel to {RAW_DIR}")
        if args.input is None:
            return 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.input:
        files = [args.input.resolve()]
    else:
        files = sorted(path for path in RAW_DIR.glob("*") if path.suffix.lower() in {".csv", ".xlsx", ".xlsm", ".xls"})
    if not files:
        print(f"No RBI CSV/Excel export found in {RAW_DIR}")
        print("Run with --open-portal, export the official DBIE Key Rates table, then run this command again.")
        return 2

    # Import only the newest candidate, preventing old snapshots from silently
    # overriding a newer report; each source export remains untouched.
    source = max(files, key=lambda path: path.stat().st_mtime)
    try:
        output, manifest_path, manifest = convert_export(source)
    except (OSError, ValueError, ImportError) as exc:
        print(f"RBI import failed: {exc}", file=sys.stderr)
        return 1
    print(f"Imported source: {source}")
    print(f"Observations: {manifest['observation_count']} ({manifest['start_date']} to {manifest['end_date']})")
    print(f"Canonical data: {output}")
    print(f"Provenance manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
