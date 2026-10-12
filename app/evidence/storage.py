"""File storage for evidence uploads."""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.config import get_evidence_limits
from app.evidence.schemas import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    EvidenceFormat,
    EvidenceMetadata,
    EvidenceStatus,
)


class EvidenceStorage:
    """Handles secure file storage for evidence uploads."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            if os.getenv("VERCEL", "").lower() == "1":
                base_dir = Path("/tmp/artha-ai-evidence")
            else:
                base_dir = Path(__file__).resolve().parents[2] / "data" / "uploads"
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._limits = get_evidence_limits()

    @property
    def max_file_size(self) -> int:
        return self._limits["max_upload_mb"] * 1024 * 1024

    def _get_run_dir(self, run_id: str) -> Path:
        """Get the directory for a specific run."""
        # Validate run_id is a valid UUID to prevent path traversal
        try:
            uuid.UUID(run_id)
        except ValueError:
            raise ValueError("Invalid run_id format")
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _metadata_path(self, run_id: str, evidence_id: str) -> Path:
        if not evidence_id or any(char not in "0123456789abcdef" for char in evidence_id.lower()):
            raise ValueError("Invalid evidence_id format")
        return self._get_run_dir(run_id) / f"{evidence_id}.meta.json"

    def save_metadata(self, metadata: EvidenceMetadata) -> None:
        path = self._metadata_path(metadata.run_id, metadata.evidence_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def load_metadata(self, run_id: str, evidence_id: str) -> Optional[EvidenceMetadata]:
        path = self._metadata_path(run_id, evidence_id)
        if not path.is_file():
            return None
        return EvidenceMetadata.model_validate_json(path.read_text(encoding="utf-8"))

    def list_metadata(self, run_id: str) -> list[EvidenceMetadata]:
        run_dir = self._get_run_dir(run_id)
        entries = []
        for path in run_dir.glob("*.meta.json"):
            try:
                entries.append(EvidenceMetadata.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return sorted(entries, key=lambda item: item.uploaded_at)

    def list_all_metadata(self) -> list[EvidenceMetadata]:
        """Read persisted metadata across local run directories for retention cleanup."""
        entries: list[EvidenceMetadata] = []
        for run_dir in self.base_dir.iterdir():
            if not run_dir.is_dir():
                continue
            try:
                uuid.UUID(run_dir.name)
            except ValueError:
                continue
            entries.extend(self.list_metadata(run_dir.name))
        return entries

    def delete_metadata(self, run_id: str, evidence_id: str) -> bool:
        path = self._metadata_path(run_id, evidence_id)
        if path.is_file():
            path.unlink()
            return True
        return False

    def _generate_stored_filename(self, original_filename: str) -> str:
        """Generate a secure stored filename."""
        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".bin"
        return f"{uuid.uuid4().hex}{ext}"

    def _compute_sha256(self, file: BinaryIO) -> str:
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        for chunk in iter(lambda: file.read(8192), b""):
            hasher.update(chunk)
        file.seek(0)
        return hasher.hexdigest()

    def validate_file(
        self, filename: str, mime_type: str, file_size: int
    ) -> tuple[bool, Optional[str]]:
        """Validate file extension, MIME type, and size."""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File extension '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

        expected_mimes = {
            ".pdf": {"application/pdf"},
            ".csv": {"text/csv", "application/csv", "text/plain"},
            ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            ".json": {"application/json", "text/plain"},
            ".txt": {"text/plain", "text/markdown"},
            ".md": {"text/plain", "text/markdown"},
        }
        if mime_type not in expected_mimes[ext]:
            return False, f"MIME type does not match the {ext} file format."

        if mime_type not in ALLOWED_MIME_TYPES:
            return False, f"MIME type '{mime_type}' not allowed."

        if file_size > self.max_file_size:
            return False, f"File size {file_size} bytes exceeds maximum of {self.max_file_size} bytes ({self._limits['max_upload_mb']} MB)."

        if file_size == 0:
            return False, "Empty files are not allowed."

        return True, None

    def validate_run_file_count(self, run_id: str) -> tuple[bool, Optional[str]]:
        """Check if run has reached max files limit."""
        run_dir = self._get_run_dir(run_id)
        if run_dir.exists():
            file_count = len(list(run_dir.glob("*.meta.json")))
            if file_count >= self._limits["max_files_per_run"]:
                return False, f"Run has reached maximum of {self._limits['max_files_per_run']} files."
        return True, None

    def save_upload(
        self,
        run_id: str,
        original_filename: str,
        mime_type: str,
        file: BinaryIO,
        file_size: int,
    ) -> tuple[EvidenceMetadata, Path]:
        """Save an uploaded file and return metadata and path."""
        # Validate file
        valid, error = self.validate_file(original_filename, mime_type, file_size)
        if not valid:
            raise ValueError(error)

        # Validate run file count
        valid, error = self.validate_run_file_count(run_id)
        if not valid:
            raise ValueError(error)

        # Generate secure filename
        stored_filename = self._generate_stored_filename(original_filename)
        run_dir = self._get_run_dir(run_id)
        file_path = run_dir / stored_filename
        temporary_path = run_dir / f"{stored_filename}.part"

        # Compute hash while saving
        hasher = hashlib.sha256()
        try:
            with open(temporary_path, "xb") as f:
                for chunk in iter(lambda: file.read(8192), b""):
                    hasher.update(chunk)
                    f.write(chunk)
            temporary_path.replace(file_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        sha256 = hasher.hexdigest()

        # Determine format
        ext = Path(original_filename).suffix.lower().lstrip(".")
        format_enum = EvidenceFormat(ext)

        metadata = EvidenceMetadata(
            evidence_id=uuid.uuid4().hex,
            run_id=run_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            size=file_size,
            sha256=sha256,
            uploaded_at=datetime.now(timezone.utc),
            format=format_enum,
            status=EvidenceStatus.UPLOADING,
        )

        return metadata, file_path

    def get_file_path(self, run_id: str, stored_filename: str) -> Path:
        """Get the full path to a stored file."""
        run_dir = self._get_run_dir(run_id)
        file_path = run_dir / stored_filename
        # Ensure path is within run_dir (prevent path traversal)
        try:
            file_path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            raise ValueError("Invalid file path")
        return file_path

    def delete_file(self, run_id: str, stored_filename: str) -> bool:
        """Delete a stored file."""
        try:
            file_path = self.get_file_path(run_id, stored_filename)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except ValueError:
            return False

    def list_run_files(self, run_id: str) -> list[Path]:
        """List all files for a run."""
        run_dir = self._get_run_dir(run_id)
        if run_dir.exists():
            return list(run_dir.iterdir())
        return []

    def cleanup_run(self, run_id: str) -> bool:
        """Delete all files for a run."""
        run_dir = self._get_run_dir(run_id)
        if run_dir.exists():
            shutil.rmtree(run_dir)
            return True
        return False


# Global storage instance
_storage: Optional[EvidenceStorage] = None


def get_storage() -> EvidenceStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = EvidenceStorage()
    return _storage
