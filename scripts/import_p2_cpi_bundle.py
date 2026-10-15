"""Install a verified P2 model bundle exported by notebooks/train2.ipynb."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app" / "models" / "p2_cpi_benchmark_assets"
DATA_FILE = PACKAGE / "source" / "master_data1.csv"
DESTINATION = PACKAGE / "artifacts"
EXPECTED_COMMIT = "ce8abb01d2ec0fd7524638995281e32a8142f1d1"
EXPECTED_DATASET_SHA256 = "5ce2206c99358cc5816de7372fb6d1fe1952348834f5c4f273d03ed55135ae7f"
EXPECTED_FILES = {
    "arima_300.joblib",
    "arimax_300.joblib",
    "elasticnet.joblib",
    "xgboost.joblib",
    "walk_forward_metrics.csv",
    "walk_forward_predictions.csv",
    "training_metadata.json",
    "LICENSE-p2-india-cpi-forecasting.txt",
    "README.txt",
}
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_bundle(bundle: Path, staging: Path) -> None:
    if not DATA_FILE.is_file() or _sha256(DATA_FILE) != EXPECTED_DATASET_SHA256:
        raise ValueError("The pinned P2 dataset is missing or failed its SHA-256 check.")
    with zipfile.ZipFile(bundle) as archive:
        members = [entry for entry in archive.infolist() if not entry.is_dir()]
        names = [entry.filename for entry in members]
        if len(names) != len(set(names)):
            raise ValueError("The model ZIP contains duplicate filenames.")
        if set(names) != EXPECTED_FILES:
            raise ValueError(
                f"Unexpected model ZIP contents; missing={sorted(EXPECTED_FILES - set(names))}, "
                f"extra={sorted(set(names) - EXPECTED_FILES)}"
            )
        total_size = 0
        for entry in members:
            relative = PurePosixPath(entry.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in entry.filename:
                raise ValueError(f"Unsafe path in model ZIP: {entry.filename!r}")
            total_size += entry.file_size
        if total_size > MAX_ARCHIVE_BYTES:
            raise ValueError("The uncompressed model ZIP exceeds the 20 MiB safety limit.")
        for entry in members:
            target = staging.joinpath(*PurePosixPath(entry.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)

    license_path = staging / "LICENSE-p2-india-cpi-forecasting.txt"
    source_license = DATA_FILE.parent / "LICENSE"
    if license_path.read_bytes() != source_license.read_bytes():
        raise ValueError("The model bundle's MIT license does not match the pinned source license.")
    metadata_path = staging / "training_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("The model bundle metadata must be a JSON object.")
    if metadata.get("source_commit") != EXPECTED_COMMIT:
        raise ValueError("The model bundle was not trained from the pinned P2 repository commit.")
    if metadata.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
        raise ValueError("The model bundle's dataset checksum does not match the pinned P2 dataset.")
    if metadata.get("source_license") != "MIT (see LICENSE-p2-india-cpi-forecasting.txt)":
        raise ValueError("The model bundle is missing its expected MIT license reference.")
    if metadata.get("target") != "cpi_inflation":
        raise ValueError("The model bundle has an unexpected target definition.")
    if int(metadata.get("validation", {}).get("test_observations", 0)) != 52:
        raise ValueError("The model bundle does not contain the expected 52-origin evaluation.")
    if metadata.get("models") != ["arima_300", "arimax_300", "elasticnet", "xgboost"]:
        raise ValueError("The model bundle's model inventory does not match the expected training run.")
    empty_files = [name for name in EXPECTED_FILES if (staging / name).stat().st_size == 0]
    if empty_files:
        raise ValueError(f"The model bundle contains empty files: {sorted(empty_files)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path, help="ZIP exported from train2.ipynb")
    args = parser.parse_args()
    bundle = args.bundle.expanduser().resolve()
    if not bundle.is_file():
        raise FileNotFoundError(f"Model bundle does not exist: {bundle}")
    if bundle.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("The model ZIP exceeds the 20 MiB safety limit.")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing model artifacts at {DESTINATION}; "
            "move the existing package aside before importing another run."
        )
    with tempfile.TemporaryDirectory(prefix=".p2-import-", dir=DESTINATION.parent) as temp_dir:
        staging = Path(temp_dir)
        _validate_bundle(bundle, staging)
        os.replace(staging, DESTINATION)
    print(f"Installed P2 model artifacts into {DESTINATION}")
    print("ARIMAX is included for reproducibility but will not be served: the checked run did not converge.")
    print("Only load a bundle you created in your trusted Colab runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
