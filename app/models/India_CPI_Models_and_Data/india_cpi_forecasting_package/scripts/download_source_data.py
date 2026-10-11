#!/usr/bin/env python3
"""Download the public Kaggle and official MoSPI CPI source snapshots.

This script uses only public URLs and requests no credentials. The included raw
snapshots in the ZIP are the exact files used for the shipped models; rerunning
this script may retrieve newer revisions, whose hashes must be checked.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
SOURCES = {
    "kaggle_archive": (
        "https://www.kaggle.com/api/v1/datasets/download/yatharthgupta18/all-india-consumer-price-index20132023",
        RAW / "kaggle/kaggle_india_cpi_2013_2023.zip",
    ),
    "official_archive_csv": (
        "https://www.data.gov.in/files/ogdpv2dms/s3fs-public/All_India_Index_Upto_Aug25.csv",
        RAW / "official/All_India_Index_Upto_Aug25.csv",
    ),
    "mospi_december_2025_release": (
        "https://www.mospi.gov.in/uploads/latestReleases/latest_release_1768213461321_53cd35fd-1bbc-4b43-b92d-8fb67474ee74_Press_Release_of_CPI_for_December_2025.pdf",
        RAW / "official/mospi_cpi_december_2025_release.pdf",
    ),
    "mospi_january_2026_final_release": (
        "https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf",
        RAW / "official/mospi_cpi_january_2026_release.pdf",
    ),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "IndiaCPIPrototype/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target)


def main() -> None:
    manifest = {}
    for name, (url, path) in SOURCES.items():
        download(url, path)
        if name == "kaggle_archive" and not zipfile.is_zipfile(path):
            raise ValueError("Kaggle endpoint did not return a ZIP archive")
        if name.startswith("mospi_") and not path.read_bytes().startswith(b"%PDF"):
            raise ValueError(f"MoSPI endpoint did not return a PDF: {path}")
        if name == "official_archive_csv" and b"Sector,Year,Month" not in path.read_bytes()[:200]:
            # Header formatting can change, but an HTML error page must never be accepted.
            if b"<html" in path.read_bytes()[:500].lower():
                raise ValueError("Official data.gov.in endpoint returned HTML, not CSV")
        manifest[name] = {"url": url, "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        print(f"Downloaded {name}: {path.stat().st_size} bytes, sha256={manifest[name]['sha256']}")

    kaggle_zip = RAW / "kaggle/kaggle_india_cpi_2013_2023.zip"
    csv_out = RAW / "kaggle/datafile.csv"
    with zipfile.ZipFile(kaggle_zip) as archive:
        candidates = [n for n in archive.namelist() if Path(n).name.lower() == "datafile.csv"]
        if not candidates:
            raise FileNotFoundError("No datafile.csv was found in the Kaggle archive")
        with tempfile.TemporaryDirectory() as temp:
            archive.extract(candidates[0], temp)
            csv_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(temp) / candidates[0], csv_out)
    manifest["kaggle_csv"] = {"path": str(csv_out.relative_to(ROOT)), "bytes": csv_out.stat().st_size, "sha256": sha256(csv_out)}

    for key, pdf in [("december_text", RAW / "official/mospi_cpi_december_2025_release.pdf"),
                     ("final_text", RAW / "official/mospi_cpi_january_2026_release.pdf")]:
        text_path = pdf.with_suffix(".txt")
        subprocess.run(["pdftotext", "-layout", str(pdf), str(text_path)], check=True)
        manifest[key] = {"path": str(text_path.relative_to(ROOT)), "bytes": text_path.stat().st_size, "sha256": sha256(text_path)}
    out = RAW / "download_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
