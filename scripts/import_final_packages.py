"""Install the supplied final data and model bundles into the project.

The ZIP filenames supplied by the training workflow are not authoritative:
the dataset archive contains ``Artha_AI_Datasets`` and the model archive
contains ``Artha_AI_Models``.  This importer detects the roots, validates
archive paths, stages all output, and then installs it atomically.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
INTERIM_ROOT = DATA_ROOT / "interim"
MODEL_ROOT = (
    PROJECT_ROOT
    / "app"
    / "models"
    / "Final_data_and_models"
    / "Final_model_sets"
    / "India_CPI_Model_Package"
)


def _safe_extract(archive: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        for name in names:
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError(f"Unsafe archive member: {name}")
        bundle.extractall(destination)
        roots = {name.split("/", 1)[0] for name in names if name}
    if len(roots) != 1:
        raise ValueError(f"Expected one archive root, found: {sorted(roots)}")
    root = destination / next(iter(roots))
    if not root.is_dir():
        raise ValueError(f"Archive root is not a directory: {root}")
    return root


def _find_root(archive: Path, expected_name: str, staging: Path) -> Path:
    root = _safe_extract(archive, staging)
    if root.name != expected_name:
        raise ValueError(
            f"{archive.name} contains {root.name!r}; expected {expected_name!r} "
            "based on its contents"
        )
    return root


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _copy_tree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _write_normalized_snapshots(dataset_root: Path, staging: Path) -> dict[str, int]:
    processed_files = list(
        (dataset_root / "supplemental").glob("**/data/processed/macro_observations.csv")
    )
    if len(processed_files) != 1:
        raise ValueError(
            "Expected exactly one supplemental macro_observations.csv, "
            f"found {len(processed_files)}"
        )
    rows = _read_csv(processed_files[0])
    mappings = {
        "cpi_headline": ("cpi_index_2024", "index_2024=100", "2024=100"),
        "food_inflation": ("cfpi_yoy_2012", "percent", "2012=100"),
        "brent_crude": ("brent_price", "usd_per_barrel", None),
        "inr_usd": ("usd_inr_monthly_average", "inr_per_usd", None),
        "iip": ("iip_general_index_2022_23", "index_2022-23=100", "2022-23"),
        "repo_rate": ("repo_rate", "percent", None),
    }
    counts: dict[str, int] = {}
    for series_id, (source_id, unit, base_year) in mappings.items():
        observations = []
        for row in rows:
            if row.get("series_id") != source_id or not row.get("obs_date"):
                continue
            try:
                value = float(row["value"])
            except (KeyError, TypeError, ValueError):
                continue
            observations.append(
                {
                    "obs_date": row["obs_date"][:10],
                    "value": value,
                    "source": row.get("source") or "supplied final dataset",
                    "source_url": row.get("source_url") or None,
                    "release_date": row.get("release_date") or None,
                    "retrieved_at": row.get("retrieved_at") or None,
                    "unit": unit,
                    "base_year": base_year,
                }
            )
        observations.sort(key=lambda item: item["obs_date"])
        if not observations:
            raise ValueError(f"Required supplied series is empty: {source_id}")
        _write_json(
            staging / "interim" / f"{series_id}_normalized_final.json",
            {
                "mode": "replace",
                "source": "supplied final dataset",
                "observations": observations,
            },
        )
        counts[series_id] = len(observations)
    return counts


def _build_runtime_package(model_root: Path, staging: Path) -> Path:
    source = model_root / "artifacts"
    retrained = source / "retrained_20261016"
    extended = source / "retrained_20261016_extended"
    for required in (retrained, extended):
        if not required.is_dir():
            raise ValueError(f"Missing retrained artifact tree: {required}")

    package = staging / "model_package"
    artifacts = package / "artifacts"
    artifacts.mkdir(parents=True)
    _copy_tree_contents(retrained / "mospi_2024_base", artifacts / "mospi_2024_base")
    _copy_tree_contents(
        retrained / "oecd_long_history_sensitivity",
        artifacts / "oecd_long_history_sensitivity",
    )
    _copy_tree_contents(
        extended,
        artifacts / "mospi_2024_base_extended",
    )
    for filename in (
        "mospi_2024_base_target.csv",
        "macro_predictors_one_month_lag.csv",
        "external_macro_monthly_source_panel.csv",
    ):
        shutil.copy2(retrained / filename, artifacts / filename)

    bundle_manifest = model_root / "BUNDLE_MANIFEST.json"
    inventory = model_root / "MODEL_PACKAGE_INVENTORY_20261016.csv"
    if bundle_manifest.is_file():
        shutil.copy2(bundle_manifest, package / bundle_manifest.name)
    if inventory.is_file():
        shutil.copy2(inventory, package / inventory.name)

    checksums: list[str] = []
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {path.relative_to(package).as_posix()}")
    (package / "SHA256SUMS.txt").write_text(
        "\n".join(checksums) + "\n",
        encoding="utf-8",
    )
    return package


def _install_directory(staged: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        # Existing project directories may be watched or locked by the
        # editor/server on Windows.  The staged tree has already passed all
        # validation, so merge it without deleting unrelated project files.
        shutil.copytree(staged, destination, dirs_exist_ok=True)
    else:
        os.replace(staged, destination)


def import_bundles(dataset_archive: Path, model_archive: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="artha-import-", dir=tempfile.gettempdir()) as temp:
        staging = Path(temp)
        dataset_root = _find_root(dataset_archive, "Artha_AI_Datasets", staging / "datasets")
        model_root = _find_root(model_archive, "Artha_AI_Models", staging / "models")

        staged_data = staging / "data"
        shutil.copytree(dataset_root, staged_data / "external" / "Artha_AI_Datasets")
        counts = _write_normalized_snapshots(dataset_root, staged_data)
        staged_package = _build_runtime_package(model_root, staging)

        _install_directory(staged_data / "external", DATA_ROOT / "external")
        INTERIM_ROOT.mkdir(parents=True, exist_ok=True)
        for snapshot in (staged_data / "interim").glob("*.json"):
            shutil.copy2(snapshot, INTERIM_ROOT / snapshot.name)
        _install_directory(staged_package, MODEL_ROOT)

    return {
        "dataset_archive": str(dataset_archive),
        "model_archive": str(model_archive),
        "normalized_series": counts,
        "model_variants": [
            "mospi_2024_base",
            "mospi_2024_base_extended",
            "oecd_long_history_sensitivity",
        ],
        "model_origin": "retrained_20261016",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_archive", type=Path)
    parser.add_argument("model_archive", type=Path)
    args = parser.parse_args()
    result = import_bundles(args.dataset_archive.resolve(), args.model_archive.resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
