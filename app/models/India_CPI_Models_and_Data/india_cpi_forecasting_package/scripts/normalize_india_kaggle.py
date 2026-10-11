#!/usr/bin/env python3
"""Normalize India CPI data, preserving source vintages and missing observations.

Kaggle CPI category/sector observations are retained as observed features. Their
full overlap with the archived first-party data.gov.in snapshot is audited cell
by cell. The model target is MoSPI's directly published All-India General CPI
YoY rate (2012=100) from the final old-base time series. No synthetic values or
interpolation are used.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
KAGGLE_ZIP = RAW / "kaggle/kaggle_india_cpi_2013_2023.zip"
KAGGLE_CSV = RAW / "kaggle/datafile.csv"
ARCHIVE_CSV = RAW / "official/All_India_Index_Upto_Aug25.csv"
DEC_RELEASE_PDF = RAW / "official/mospi_cpi_december_2025_release.pdf"
DEC_RELEASE_TEXT = RAW / "official/mospi_cpi_december_2025_release.txt"
FINAL_RELEASE_PDF = RAW / "official/mospi_cpi_january_2026_release.pdf"
FINAL_RELEASE_TEXT = RAW / "official/mospi_cpi_january_2026_release.txt"
OUT = ROOT / "data/processed"
REPORTS = ROOT / "reports"

SOURCES = {
    "kaggle_listing": "https://www.kaggle.com/datasets/yatharthgupta18/all-india-consumer-price-index20132023",
    "kaggle_download_api": "https://www.kaggle.com/api/v1/datasets/download/yatharthgupta18/all-india-consumer-price-index20132023",
    "official_catalog": "https://www.data.gov.in/catalog/all-india-consumer-price-index-ruralurban-0",
    "official_archive_resource": "https://www.data.gov.in/resource/all-india-consumer-price-index-ruralurban-upto-august-2025",
    "official_archive_csv": "https://www.data.gov.in/files/ogdpv2dms/s3fs-public/All_India_Index_Upto_Aug25.csv",
    "official_december_2025_release": "https://www.mospi.gov.in/uploads/latestReleases/latest_release_1768213461321_53cd35fd-1bbc-4b43-b92d-8fb67474ee74_Press_Release_of_CPI_for_December_2025.pdf",
    "official_january_2026_final_release": "https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf",
}

MONTHS = {
    name: i
    for i, name in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"],
        start=1,
    )
}
MONTH_ALIASES = {"Marcrh": "March"}
SECTORS = ["Rural", "Urban", "Rural+Urban"]
SECTOR_CANONICAL = {"Rural": "rural", "Urban": "urban", "Rural+Urban": "combined"}
META_COLS = {"Sector", "Year", "Month", "period"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def column_slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def load_source(path: Path, source_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, na_values=["NA", "-"])
    frame.columns = frame.columns.astype(str).str.strip()
    required = {"Sector", "Year", "Month", "General index"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{source_name}: missing required columns {required - set(frame.columns)}")

    frame["Sector"] = frame["Sector"].astype(str).str.replace("\u00a0", " ", regex=False).str.strip()
    frame["Month_clean"] = frame["Month"].astype(str).str.replace("\u00a0", " ", regex=False).str.strip().str.title()
    frame["Month_clean"] = frame["Month_clean"].replace(MONTH_ALIASES)
    frame["Year_num"] = pd.to_numeric(frame["Year"], errors="coerce")
    frame["Month_num"] = frame["Month_clean"].map(MONTHS)
    bad = frame["Year_num"].isna() | frame["Month_num"].isna() | ~frame["Sector"].isin(SECTORS)
    if bad.any():
        raise ValueError(f"{source_name}: invalid date/sector rows:\n{frame.loc[bad, ['Sector','Year','Month']].head(10)}")
    frame["Year_num"] = frame["Year_num"].astype(int)
    frame["Month_num"] = frame["Month_num"].astype(int)
    frame["period"] = pd.PeriodIndex(
        frame["Year_num"].astype(str) + "-" + frame["Month_num"].astype(str).str.zfill(2),
        freq="M",
    )

    value_cols = [c for c in frame.columns if c not in META_COLS | {"Month_clean", "Year_num", "Month_num"}]
    for col in value_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if frame.duplicated(["Sector", "period"]).any():
        duplicates = frame.loc[frame.duplicated(["Sector", "period"], keep=False), ["Sector", "period"]]
        raise ValueError(f"{source_name}: duplicate sector-months:\n{duplicates.head(10)}")
    frame["_source_name"] = source_name
    return frame


def parse_pdf_monthly_table(text: str, first_year: int, last_year: int) -> pd.Series:
    """Parse a twelve-month annual table from an extracted MoSPI PDF section."""
    observations: dict[pd.Period, float] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*(20\d{2})\s+(.*)$", line)
        if not match:
            continue
        year = int(match.group(1))
        if year < first_year or year > last_year:
            continue
        tokens = re.findall(r"(?<!\S)(?:\d+(?:\.\d*)?|-)(?:\*)?(?=\s|$)", match.group(2))
        if len(tokens) != 12:
            continue
        for month, token in enumerate(tokens, start=1):
            value = np.nan if token == "-" else float(token.replace("*", ""))
            observations[pd.Period(f"{year}-{month:02d}", freq="M")] = value
    return pd.Series(observations, dtype="float64").sort_index()


def parse_final_series() -> tuple[pd.Series, pd.Series]:
    if not DEC_RELEASE_TEXT.exists():
        subprocess.run(["pdftotext", "-layout", str(DEC_RELEASE_PDF), str(DEC_RELEASE_TEXT)], check=True)
    if not FINAL_RELEASE_TEXT.exists():
        subprocess.run(["pdftotext", "-layout", str(FINAL_RELEASE_PDF), str(FINAL_RELEASE_TEXT)], check=True)
    text = DEC_RELEASE_TEXT.read_text(encoding="utf-8", errors="replace")
    vi_matches = list(re.finditer(r"(?m)^\s*Annexure VI\s*$", text))
    vii_matches = list(re.finditer(r"(?m)^\s*Annexure VII\s*$", text))
    if not vi_matches or not vii_matches or vi_matches[-1].start() >= vii_matches[-1].start():
        raise ValueError("Could not locate the exact Annexure VI and VII headings in MoSPI PDF text")
    index_section = text[vi_matches[-1].end():vii_matches[-1].start()]
    yoy_section = text[vii_matches[-1].end():]
    final_index = parse_pdf_monthly_table(index_section, 2013, 2025)
    published_yoy = parse_pdf_monthly_table(yoy_section, 2014, 2025)
    expected_index = pd.period_range("2013-01", "2025-12", freq="M")
    expected_yoy = pd.period_range("2014-01", "2025-12", freq="M")
    if not final_index.index.equals(expected_index) or final_index.isna().any():
        raise ValueError(f"Unexpected official final index table coverage: {len(final_index)} rows")
    if not published_yoy.index.equals(expected_yoy) or published_yoy.notna().sum() != 142:
        raise ValueError(f"Unexpected official published YoY table coverage: {len(published_yoy)} rows")

    # The later release finalizes December 2025 at the old 2012 base. Check the
    # Annexure VI/VII endpoint against the final (not provisional) publication.
    final_text = FINAL_RELEASE_TEXT.read_text(encoding="utf-8", errors="replace")
    final_section = final_text.split("December, 2025 (Final) at Base 2012=100", 1)[-1].split("III.", 1)[0]
    flattened = re.sub(r"\s+", " ", final_section)
    inflation_match = re.search(r"CPI\s*\(General\)\s+0\.76\s+2\.03\s+([0-9.]+)", flattened)
    index_match = re.search(r"CPI\s*\(General\)\s+199\.9\s+195\.9\s+([0-9.]+)", flattened)
    if not inflation_match or not index_match:
        raise ValueError("Could not verify the final December 2025 old-base CPI figures in the February release")
    if abs(float(inflation_match.group(1)) - published_yoy.loc[pd.Period("2025-12", freq="M")]) > 1e-10:
        raise ValueError("December 2025 final published rate differs from the parsed time-series table")
    if abs(float(index_match.group(1)) - final_index.loc[pd.Period("2025-12", freq="M")]) > 1e-10:
        raise ValueError("December 2025 final index differs from the parsed time-series table")
    return final_index, published_yoy


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, na_rep="")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    kaggle = load_source(KAGGLE_CSV, "kaggle_mirror")
    archive = load_source(ARCHIVE_CSV, "mospidata_gov_in_archived_snapshot")
    final_index, published_yoy = parse_final_series()

    measure_cols = [c for c in kaggle.columns if c not in META_COLS | {"Month_clean", "Year_num", "Month_num", "_source_name"}]
    archive_measure_cols = [c for c in archive.columns if c not in META_COLS | {"Month_clean", "Year_num", "Month_num", "_source_name"}]
    if measure_cols != archive_measure_cols:
        raise ValueError("Kaggle and official archived sources have different measurement schemas")

    # Exact audit of the complete Kaggle/file overlap, including missingness.
    overlap = kaggle.merge(archive, on=["Sector", "period"], suffixes=("_k", "_o"), how="inner", validate="one_to_one")
    overlap_mismatches = 0
    overlap_cells = 0
    for col in measure_cols:
        left, right = overlap[f"{col}_k"], overlap[f"{col}_o"]
        overlap_cells += len(overlap)
        mismatch = (left.isna() != right.isna()) | (left.notna() & right.notna() & ((left - right).abs() > 1e-10))
        overlap_mismatches += int(mismatch.sum())
    if overlap_mismatches:
        raise ValueError(f"Kaggle and official archived overlap disagrees in {overlap_mismatches} measurement cells")

    calendar = pd.period_range("2013-01", "2025-12", freq="M")
    kaggle_lookup = kaggle.set_index(["Sector", "period"])
    archive_lookup = archive.set_index(["Sector", "period"])
    kaggle_last = kaggle.groupby("Sector")["period"].max().to_dict()
    archive_last = archive.groupby("Sector")["period"].max().to_dict()
    archive_rows = []
    wide_rows = []

    for period in calendar:
        row: dict[str, Any] = {"period": str(period), "country": "India", "country_code": "IND"}
        for sector in SECTORS:
            key = (sector, period)
            k_present = key in kaggle_lookup.index
            a_present = key in archive_lookup.index
            k_row = kaggle_lookup.loc[key] if k_present else None
            a_row = archive_lookup.loc[key] if a_present else None
            cs = SECTOR_CANONICAL[sector]
            row[f"{cs}__archive_source"] = (
                "Kaggle mirror (exact overlap match)" if k_present
                else ("MoSPI/data.gov.in archived extension" if a_present else "no archive source row")
            )
            row[f"{cs}__kaggle_last_period"] = str(kaggle_last.get(sector, ""))
            row[f"{cs}__official_archive_last_period"] = str(archive_last.get(sector, ""))

            for measure in measure_cols:
                kval = float(k_row[measure]) if k_present and pd.notna(k_row[measure]) else np.nan
                aval = float(a_row[measure]) if a_present and pd.notna(a_row[measure]) else np.nan
                if np.isfinite(kval):
                    value, source_label, source_url = kval, "Kaggle mirror; exact match in official archived overlap", SOURCES["kaggle_listing"]
                elif np.isfinite(aval):
                    value, source_label, source_url = aval, "MoSPI/data.gov.in archived observation or fallback", SOURCES["official_archive_csv"]
                else:
                    value, source_label = np.nan, "not observed in either archived snapshot"
                    source_url = SOURCES["kaggle_listing"] if k_present else SOURCES["official_archive_csv"]

                slug = column_slug(measure)
                suffix = "_archive_snapshot" if measure == "General index" else ""
                row[f"{cs}__{slug}_index_2012_100{suffix}"] = value
                archive_rows.append({
                    "country": "India", "country_code": "IND", "sector": cs, "period": str(period),
                    "indicator": f"{measure} (Kaggle/data.gov.in archived snapshot)", "value": value,
                    "unit": "CPI index, 2012=100", "observation_status": "observed" if np.isfinite(value) else "missing_or_not_in_snapshot",
                    "source_used": source_label, "source_url": source_url,
                    "kaggle_row_present": bool(k_present), "official_archive_row_present": bool(a_present),
                })
        wide_rows.append(row)

    panel = pd.DataFrame(wide_rows)
    final_index = final_index.reindex(calendar)
    published_yoy = published_yoy.reindex(calendar)
    archive_combined_col = "combined__general_index_index_2012_100_archive_snapshot"
    archive_combined = pd.Series(panel[archive_combined_col].to_numpy(dtype="float64"), index=calendar)
    final_derived_yoy = 100.0 * (final_index / final_index.shift(12) - 1.0)
    archive_derived_yoy = 100.0 * (archive_combined / archive_combined.shift(12) - 1.0)

    pdf_yoy_valid = published_yoy.notna() & final_derived_yoy.notna()
    pdf_derived_diff = (published_yoy[pdf_yoy_valid] - final_derived_yoy[pdf_yoy_valid]).abs()
    if len(pdf_derived_diff) != 142 or float(pdf_derived_diff.max()) > 0.01:
        raise ValueError("Official published YoY series does not reconcile to its rounded 2012-base index within 0.01 pp")

    archive_valid = archive_combined.notna() & final_index.notna()
    archive_diff = (archive_combined[archive_valid] - final_index[archive_valid]).abs()
    archive_index_mismatch_count = int((archive_diff > 1e-10).sum())
    archive_index_max_diff = float(archive_diff.max()) if len(archive_diff) else np.nan
    target_compare = published_yoy.notna() & archive_derived_yoy.notna()
    target_vintage_diff = (published_yoy[target_compare] - archive_derived_yoy[target_compare]).abs()

    panel["headline_cpi_index_2012_100_final"] = final_index.values
    panel["headline_cpi_yoy_pct"] = published_yoy.values
    panel["headline_cpi_yoy_pct_derived_from_final_index"] = final_derived_yoy.values
    panel["headline_cpi_yoy_pct_derived_from_archive_index"] = archive_derived_yoy.values
    panel["headline_target_status"] = np.select(
        [panel["headline_cpi_yoy_pct"].notna(), panel["period"].str.slice(0, 7) < "2014-01"],
        ["observed_official_published", "not_yet_a_12_month_target"],
        default="official_published_rate_missing",
    )
    panel["headline_target_source"] = "MoSPI December 2025 release Annexure VII; December 2025 final cross-check"
    panel["index_base"] = "2012=100"
    panel["synthetic_data_used"] = False

    target = panel[[
        "period", "country", "country_code", "headline_cpi_index_2012_100_final", "headline_cpi_yoy_pct",
        "headline_cpi_yoy_pct_derived_from_final_index", "headline_cpi_yoy_pct_derived_from_archive_index",
        "headline_target_status", "headline_target_source", "index_base", "synthetic_data_used",
    ]].copy()

    # Add authoritative final index levels and directly published YoY to the
    # long-form observation file as separate measures from the Kaggle vintage.
    final_rows = []
    for period, value in final_index.items():
        final_rows.append({
            "country": "India", "country_code": "IND", "sector": "combined", "period": str(period),
            "indicator": "All-India General CPI (final 2012-base series)", "value": float(value),
            "unit": "CPI index, 2012=100", "observation_status": "observed",
            "source_used": "MoSPI December 2025 release Annexure VI; endpoint finalized in February 2026 release",
            "source_url": SOURCES["official_december_2025_release"],
            "kaggle_row_present": False, "official_archive_row_present": False,
        })
    for period, value in published_yoy.items():
        final_rows.append({
            "country": "India", "country_code": "IND", "sector": "combined", "period": str(period),
            "indicator": "All-India General CPI YoY inflation rate (published)",
            "value": float(value) if pd.notna(value) else np.nan,
            "unit": "percent year-over-year", "observation_status": "observed" if pd.notna(value) else "official_rate_not_published",
            "source_used": "MoSPI December 2025 release Annexure VII; December 2025 final cross-check",
            "source_url": SOURCES["official_december_2025_release"],
            "kaggle_row_present": False, "official_archive_row_present": False,
        })
    long = pd.concat([pd.DataFrame(archive_rows), pd.DataFrame(final_rows)], ignore_index=True)

    write_csv(long, OUT / "india_cpi_observations_long.csv")
    write_csv(panel, OUT / "india_cpi_monthly_panel.csv")
    write_csv(target, OUT / "india_headline_cpi_target.csv")

    kaggle_max = {s: str(p) for s, p in kaggle.groupby("Sector")["period"].max().items()}
    archive_max = {s: str(p) for s, p in archive.groupby("Sector")["period"].max().items()}
    kaggle_rows_by_sector = {s: int(n) for s, n in kaggle.groupby("Sector").size().items()}
    archive_rows_by_sector = {s: int(n) for s, n in archive.groupby("Sector").size().items()}
    final_missing_yoy = [str(p) for p in published_yoy.index[published_yoy.isna()]]
    manifest = {
        "project": "India monthly headline CPI forecasting — Kaggle features + final official target",
        "target": "MoSPI-published All-India General CPI YoY inflation rate, 2012=100 series",
        "target_source": SOURCES["official_december_2025_release"],
        "target_formula_check": "Published YoY compared with 100 * (final index_t / final index_t-12 - 1); published rate is the model label.",
        "model_calendar_start": str(calendar.min()),
        "model_calendar_end": str(calendar.max()),
        "model_calendar_month_count": int(len(calendar)),
        "published_yoy_observed_count": int(published_yoy.notna().sum()),
        "published_yoy_missing_periods": final_missing_yoy,
        "synthetic_data_used": False,
        "missing_values_interpolated": False,
        "sources": SOURCES,
        "source_files": {
            str(p.relative_to(ROOT)): {"sha256": sha256(p), "bytes": p.stat().st_size}
            for p in [KAGGLE_ZIP, KAGGLE_CSV, ARCHIVE_CSV, DEC_RELEASE_PDF, DEC_RELEASE_TEXT, FINAL_RELEASE_PDF, FINAL_RELEASE_TEXT]
        },
        "kaggle_rows": int(len(kaggle)),
        "kaggle_rows_by_sector": kaggle_rows_by_sector,
        "official_archive_rows": int(len(archive)),
        "official_archive_rows_by_sector": archive_rows_by_sector,
        "kaggle_last_period_by_sector": kaggle_max,
        "official_archive_last_period_by_sector": archive_max,
        "overlap_sector_month_rows": int(len(overlap)),
        "overlap_measurement_cells_compared": int(overlap_cells),
        "kaggle_vs_official_archive_mismatched_cells": int(overlap_mismatches),
        "final_pdf_index_month_count": int(len(final_index)),
        "final_pdf_yoy_month_count": int((published_yoy.index >= pd.Period("2014-01", freq="M")).sum()),
        "official_published_yoy_vs_final_index_mae_pp": float(pdf_derived_diff.mean()),
        "official_published_yoy_vs_final_index_max_abs_diff_pp": float(pdf_derived_diff.max()),
        "archive_general_index_nonmissing_overlap": int(archive_valid.sum()),
        "final_pdf_index_vs_archive_index_mismatches": archive_index_mismatch_count,
        "final_pdf_index_vs_archive_max_abs_diff_points": archive_index_max_diff,
        "official_published_yoy_vs_archive_derived_yoy_overlap": int(target_compare.sum()),
        "official_published_yoy_vs_archive_derived_yoy_mae_pp": float(target_vintage_diff.mean()),
        "official_published_yoy_vs_archive_derived_yoy_max_abs_diff_pp": float(target_vintage_diff.max()),
        "official_published_yoy_vs_archive_derived_yoy_diffs_over_0_02_pp": int((target_vintage_diff > 0.02).sum()),
        "validation": {
            "kaggle_values_and_missingness_match_archived_official_overlap": True,
            "final_pdf_december_2025_index_and_yoy_match_february_2026_final_release": True,
            "official_pdf_published_yoy_consistent_with_its_rounded_index_within_0_01_pp": True,
        },
        "method_and_caveats": [
            "The downloaded Kaggle file does not reach the October 2023 endpoint claimed in its listing: it ends May 2023 for Rural/Urban and April 2023 for Rural+Urban.",
            "Kaggle and the August 2025 official archived CSV match exactly across 10,017 overlapping sector-measure cells, including missingness.",
            "The final MoSPI 2012-base index table differs from the older archived combined General index in 10 of 149 available overlapping values, by up to 2.1 index points; use the final published YoY series as the target.",
            "The final MoSPI published YoY target differs from YoY derived from the archived combined index in 135 overlapping months (MAE 0.14 pp; maximum 1.46 pp). Vintage differences are retained and reported, not silently blended.",
            "MoSPI's published target has '-' for April and May 2020; those targets remain missing even though the later final index table has index values for those months.",
            "MoSPI introduced the new 2024=100 CPI in February 2026. This package uses only the old 2012-base series and ends December 2025; do not treat it as a model trained on the current 2024-base CPI.",
            "The Kaggle/data.gov.in category indices are available through August 2025; category-derived exogenous features after that month remain missing. No values are filled or interpolated.",
            "Historical publication dates/vintages are not reconstructed. CPI category features are lagged to the last observation month, but release-timing leakage cannot be ruled out.",
        ],
    }
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / "normalization_report.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report = f"""# Normalization report — India monthly CPI

The training target is MoSPI's **published All-India General CPI year-over-year inflation rate** on the 2012=100 series. Its source table covers January 2014–December 2025 with {int(published_yoy.notna().sum())} published observations; the Ministry marks April and May 2020 with dashes. The last 2012-base value was finalized in February 2026. The published rates agree with the final table's one-decimal index-derived rates within {float(pdf_derived_diff.max()):.4f} percentage points. No target is filled or interpolated.

The Kaggle listing describes January 2013–October 2023, but the downloaded CSV actually ends {kaggle_max['Rural']} for Rural, {kaggle_max['Urban']} for Urban, and {kaggle_max['Rural+Urban']} for Rural+Urban. The Kaggle snapshot contains {len(kaggle)} rows. The first-party August 2025 data.gov.in snapshot contains {len(archive)} sector-month rows. All {overlap_cells:,} overlapping measurement cells match exactly, including missingness. Kaggle and the official archive are retained as CPI category and sector feature inputs.

MoSPI's final December 2025 2012-base General CPI index table differs from the older archived Combined General index in {archive_index_mismatch_count} of {int(archive_valid.sum())} nonmissing overlapping values, with a maximum difference of {archive_index_max_diff:.1f} index points. The directly published target differs from YoY calculated from the older archive in {int(target_compare.sum())} overlapping months (MAE {float(target_vintage_diff.mean()):.2f} pp; maximum {float(target_vintage_diff.max()):.2f} pp). The package therefore uses the final published YoY series as the target, preserves the archived series separately, and records the vintage break.

Category-level inputs from the Kaggle/data.gov.in snapshots end in August 2025. MoSPI introduced the new 2024=100 CPI in February 2026; no 2024-base observations are mixed into this package. The backtest is a prototype, not a production-readiness certification. All raw-file hashes are recorded in `source_manifest.json`.

## Sources

[1] [Kaggle India CPI dataset]({SOURCES['kaggle_listing']})
[2] [MoSPI/data.gov.in CPI archive through August 2025]({SOURCES['official_archive_resource']})
[3] [MoSPI December 2025 CPI release and Annexures VI–VII]({SOURCES['official_december_2025_release']})
[4] [MoSPI February 2026 release finalizing December 2025 at 2012=100]({SOURCES['official_january_2026_final_release']})
"""
    (REPORTS / "normalization_report.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "panel_rows": int(len(panel)),
        "long_observations": int(len(long)),
        "published_yoy_observed": int(published_yoy.notna().sum()),
        "published_yoy_missing": final_missing_yoy,
        "kaggle_official_overlap_rows": int(len(overlap)),
        "overlap_cells_compared": int(overlap_cells),
        "kaggle_archive_mismatches": int(overlap_mismatches),
        "final_index_vs_archive_mismatches": archive_index_mismatch_count,
        "final_index_max_vintage_diff": archive_index_max_diff,
        "target_vintage_mae_pp": float(target_vintage_diff.mean()),
        "kaggle_last_period": kaggle_max,
        "official_archive_last_period": archive_max,
        "final_target_last_period": str(published_yoy.index.max()),
        "output_dir": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
