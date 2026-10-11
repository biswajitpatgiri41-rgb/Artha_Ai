"""Normalize manually downloaded MoSPI CPI press-release workbooks.

Place original MoSPI Excel files in data/raw/mospi, then run:
    python -m scripts.import_mospi_excel

This imports the headline index history from Annex-IV and the all-India
Food-and-Beverages division index from Annex-I. It does not fabricate missing
months or infer release dates not present in the workbook.
"""

from __future__ import annotations

import hashlib
import json
import re
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "mospi"
INTERIM_DIR = ROOT / "data" / "interim"
MANIFEST_DIR = ROOT / "data" / "manifests"
SOURCE_URL = "https://esankhyiki.mospi.gov.in/"
BASE_YEAR = "2024=100"
FILENAME_RE = re.compile(
    r"_(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"(?P<year>20\d{2})_Annex-(?P<annex>[IV]+)\.xlsx$",
    re.IGNORECASE,
)
MONTHS = {name.lower(): number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"), start=1)}


def month_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return date(value.year, value.month, 1)
    if isinstance(value, date):
        return date(value.year, value.month, 1)
    if not isinstance(value, str):
        return None
    for fmt in ("%b-%y", "%B-%Y", "%b %Y", "%B %Y"):
        try:
            parsed = datetime.strptime(value.strip(), fmt)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    return None


def release_month(path: Path) -> tuple[int, int, str] | None:
    match = FILENAME_RE.search(path.name)
    if not match:
        return None
    return int(match.group("year")), MONTHS[match.group("month").lower()], match.group("annex").upper()


def numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if result == result and abs(result) != float("inf") else None
    except (TypeError, ValueError):
        return None


def workbook_rows(path: Path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        yield from sheet.iter_rows(values_only=True)
    finally:
        workbook.close()


def read_headline(path: Path) -> dict[date, float]:
    result: dict[date, float] = {}
    rows = list(workbook_rows(path))
    header = next((index for index, row in enumerate(rows)
                   if row and str(row[0]).strip().lower() == "month"), None)
    if header is None:
        return result
    # Annex-IV columns are Month, Rural index, Urban index, Combined index.
    for row in rows[header + 2:]:
        if not row:
            continue
        obs_date = month_date(row[0] if len(row) > 0 else None)
        value = numeric(row[3] if len(row) > 3 else None)
        if obs_date and value is not None:
            result[obs_date] = value
    return result


def read_food_division(path: Path, report_month: tuple[int, int]) -> tuple[date, float] | None:
    year, month = report_month
    for row in workbook_rows(path):
        if not row or len(row) < 5:
            continue
        name = str(row[1] or "").strip().lower()
        division_code = str(row[0] or "").strip()
        if division_code == "01" and name == "food and beverages":
            value = numeric(row[4])  # Combined index in Annex-I
            if value is not None:
                return date(year, month, 1), value
    return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_observation(series_id: str, obs_month: date, value: float,
                     retrieved_at: datetime, revision_tag: str | None) -> dict[str, Any]:
    month_end = date(obs_month.year, obs_month.month, monthrange(obs_month.year, obs_month.month)[1])
    return {
        "obs_date": month_end.isoformat(),
        "series_id": series_id,
        "value": value,
        "unit": "index_2024=100",
        "frequency": "M",
        "source": "MOSPI",
        "source_url": SOURCE_URL,
        "release_date": None,
        "base_year": BASE_YEAR,
        "seasonal_adjustment": "UNKNOWN",
        "revision_tag": revision_tag,
        "retrieved_at": retrieved_at.isoformat(),
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(RAW_DIR.glob("*.xlsx"))
    if not files:
        print(f"No .xlsx files found in {RAW_DIR}")
        return 2

    headline_candidates: dict[date, tuple[tuple[int, int], float, Path]] = {}
    food_candidates: dict[date, tuple[tuple[int, int], float, Path]] = {}
    ignored: list[str] = []

    for path in files:
        parsed = release_month(path)
        if not parsed:
            ignored.append(path.name)
            continue
        year, month, annex = parsed
        vintage = (year, month)
        if annex == "IV":
            for obs_month, value in read_headline(path).items():
                previous = headline_candidates.get(obs_month)
                if previous is None or vintage >= previous[0]:
                    headline_candidates[obs_month] = (vintage, value, path)
        elif annex == "I":
            food = read_food_division(path, (year, month))
            if food:
                obs_month, value = food
                previous = food_candidates.get(obs_month)
                if previous is None or vintage >= previous[0]:
                    food_candidates[obs_month] = (vintage, value, path)

    retrieved_at = datetime.now(timezone.utc)
    series = {
        "cpi_headline": sorted(headline_candidates.items()),
        "food_inflation": sorted(food_candidates.items()),
    }
    results = []
    for series_id, candidates in series.items():
        observations = [make_observation(
            series_id, obs_month, value, retrieved_at,
            f"MoSPI press-release vintage {vintage[0]}-{vintage[1]:02d}; release_date unavailable in workbook",
        ) for obs_month, (vintage, value, _) in candidates]
        stamp = retrieved_at.strftime("%Y%m%d_%H%M%S_%f")
        normalized = INTERIM_DIR / f"{series_id}_normalized_{stamp}.json"
        normalized.write_text(json.dumps({
            "canonical_series_id": series_id,
            "provider_series_id": "MoSPI press-release Annex-IV combined index" if series_id == "cpi_headline"
            else "MoSPI press-release Annex-I division 01 combined index",
            "source": "MOSPI",
            "observation_count": len(observations),
            "observations": observations,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        chosen_files = sorted({entry[2] for _, entry in candidates})
        dates = [obs_month for obs_month, _ in candidates]
        manifest = {
            "series_id": series_id,
            "source": "MOSPI",
            "source_url": SOURCE_URL,
            "provider_series_id": "Annex-IV combined index" if series_id == "cpi_headline"
            else "Annex-I division code 01, Food and beverages, combined index",
            "frequency": "M",
            "unit": "index_2024=100",
            "base_year": BASE_YEAR,
            "observation_count": len(observations),
            "min_date": min(dates).isoformat() if dates else None,
            "max_date": max(dates).isoformat() if dates else None,
            "release_date": None,
            "raw_files": [{"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)} for path in chosen_files],
            "normalized_file": str(normalized.relative_to(ROOT)),
            "status": "SUCCESS" if observations else "NO_MATCHING_ROWS",
            "imported_at": retrieved_at.isoformat(),
            "warnings": [],
        }
        if not observations:
            manifest["warnings"].append("No compatible observations found for this series in the supplied workbooks.")
        manifest_file = MANIFEST_DIR / f"manifest_{series_id}_mospi_excel_{stamp}.json"
        manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        results.append({"series_id": series_id, "observation_count": len(observations),
                        "min_date": manifest["min_date"], "max_date": manifest["max_date"],
                        "normalized_file": str(normalized.relative_to(ROOT)),
                        "manifest_file": str(manifest_file.relative_to(ROOT))})

    stamp = retrieved_at.strftime("%Y%m%d_%H%M%S_%f")
    report_path = MANIFEST_DIR / f"mospi_excel_import_{stamp}.json"
    report = {
        "created_at": retrieved_at.isoformat(),
        "input_directory": str(RAW_DIR.relative_to(ROOT)),
        "input_file_count": len(files),
        "results": results,
        "files_not_recognized": ignored,
        "iip_status": "NOT_FOUND: no IIP workbook was present in data/raw/mospi",
        "monthly_training_ready": False,
        "training_limitations": [
            "The supplied headline history is short and does not provide the long monthly history required for robust model training.",
            "Food CPI is imported only where Annex-I files were supplied; missing months were not filled.",
            "No IIP workbook was supplied.",
            "The workbooks do not contain an exact release date field, so release_date is left null.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for item in results:
        print(f"{item['series_id']}: {item['observation_count']} observations ({item['min_date']} to {item['max_date']})")
    print(report["iip_status"])
    print(f"Report: {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
