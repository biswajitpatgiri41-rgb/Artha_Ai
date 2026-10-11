"""Upload validation for local runtime evidence.

Uploaded documents are untrusted data. This module validates content and
resource bounds; it never executes uploaded content.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from app.core.config import get_evidence_limits

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".json", ".txt", ".md"}
MIME_BY_EXTENSION = {
    ".pdf": {"application/pdf"},
    ".csv": {"text/csv", "application/csv", "text/plain"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"},
    ".json": {"application/json", "text/plain"},
    ".txt": {"text/plain"},
    ".md": {"text/plain", "text/markdown"},
}
MAX_COLUMNS = 100
MAX_CSV_FIELD_CHARS = 1_000_000
ACTIVE_PDF_TOKENS = re.compile(rb"/(?:JavaScript|JS|OpenAction|AA|Launch|EmbeddedFiles)\b", re.IGNORECASE)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions?",
    r"disregard\s+(previous|above|all)\s+instructions?",
    r"forget\s+(everything|all|previous)",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"act\s+as\s+(a|an)\s+\w+",
    r"pretend\s+to\s+be\s+(a|an)\s+\w+",
    r"system\s*:\s*", r"assistant\s*:\s*", r"human\s*:\s*",
    r"<\|.*?\|>", r"\[INST\].*?\[/INST\]", r"<<SYS>>.*?<</SYS>>",
    r"###\s*Instruction", r"###\s*Response",
]
INJECTION_REGEXES = [re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_INJECTION_PATTERNS]


def check_path_traversal(filename: str) -> bool:
    """Reject path-like client filenames; names are metadata only."""
    normalized = os.path.normpath(filename)
    return (
        normalized.startswith("..") or os.path.isabs(normalized)
        or "/" in filename or "\\" in filename or "\x00" in filename
    )


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename).replace("\x00", "")
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename


def detect_prompt_injection(text: str) -> Tuple[bool, list[str]]:
    matches = [regex.pattern for regex in INJECTION_REGEXES if regex.search(text)]
    return bool(matches), matches


def sanitize_for_rag(text: str) -> str:
    """Bound evidence text without rewriting its meaning or treating it as instructions."""
    if not text:
        return ""
    return text[:100_000] + ("\n[TRUNCATED]" if len(text) > 100_000 else "")


def compute_file_hash(file: BinaryIO) -> str:
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file.read(8192), b""):
        hasher.update(chunk)
    file.seek(0)
    return hasher.hexdigest()


def _reject_json_constant(value: str):
    raise ValueError(f"Non-standard JSON constant: {value}")


def _pdf_validate(content: bytes, max_pages: int) -> Optional[str]:
    if not content.startswith(b"%PDF-"):
        return "File content is not a PDF"
    if ACTIVE_PDF_TOKENS.search(content):
        return "PDF contains active actions or embedded content, which are not supported"
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted:
            return "Encrypted PDFs are not supported"
        page_count = len(reader.pages)
        if page_count < 1:
            return "PDF contains no pages"
        if page_count > max_pages:
            return f"PDF exceeds the configured {max_pages} page limit"
        # Force page-tree access now so corrupt/truncated files fail at upload,
        # rather than later when indexing runs in the background.
        for page in reader.pages:
            _ = page.mediabox
        return None
    except Exception as exc:
        return f"PDF is corrupt or unreadable ({type(exc).__name__})"


def _xlsx_validate(content: bytes, limits: dict) -> Optional[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 10_000:
                return "XLSX package contains too many entries"
            if sum(item.file_size for item in members) > 100 * 1024 * 1024:
                return "XLSX workbook exceeds the safe unpacked size limit"
            if any(item.file_size and item.file_size / max(item.compress_size, 1) > 1000 for item in members):
                return "XLSX workbook compression ratio exceeds the safe limit"
            names = {item.filename for item in members}
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                return "XLSX package structure is invalid"
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                return "Macro-enabled workbooks are not supported"
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
            try:
                if len(workbook.sheetnames) > limits["max_xlsx_sheets"]:
                    return f"XLSX exceeds the configured {limits['max_xlsx_sheets']} sheet limit"
            finally:
                workbook.close()
        return None
    except Exception as exc:
        return f"XLSX package is invalid ({type(exc).__name__})"


def _csv_validate(content: bytes, max_rows: int) -> Optional[str]:
    try:
        text = content.decode("utf-8-sig")
        if "\x00" in text:
            return "CSV appears to contain binary content"
        csv.field_size_limit(min(sys.maxsize, MAX_CSV_FIELD_CHARS))
        rows = csv.reader(io.StringIO(text, newline=""))
        row_count = 0
        for row_count, row in enumerate(rows):
            if len(row) > MAX_COLUMNS:
                return f"CSV exceeds the {MAX_COLUMNS} column limit"
            if row_count > max_rows:
                return f"CSV exceeds the configured {max_rows} row limit"
        if row_count == 0:
            return "CSV is empty"
        return None
    except (UnicodeDecodeError, csv.Error, OverflowError) as exc:
        return f"CSV is invalid or unreadable ({type(exc).__name__})"


def validate_file_content(file: BinaryIO, filename: str, expected_mime: str) -> Tuple[bool, Optional[str]]:
    """Inspect actual file bytes and parser structure, independent of client MIME."""
    try:
        content = file.read()
        file.seek(0)
        if not content:
            return False, "Empty file"
        ext = Path(filename).suffix.lower()
        limits = get_evidence_limits()
        declared = MIME_BY_EXTENSION.get(ext, set())
        if expected_mime not in declared:
            return False, "Declared MIME type does not match the file extension"
        if ext == ".pdf":
            error = _pdf_validate(content, limits["max_pdf_pages"])
        elif ext == ".xlsx":
            error = _xlsx_validate(content, limits)
        elif ext == ".json":
            if len(content) > limits["max_json_bytes"]:
                error = f"JSON exceeds the configured {limits['max_json_bytes']} byte limit"
            else:
                try:
                    json.loads(content.decode("utf-8-sig"), parse_constant=_reject_json_constant)
                    error = None
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    error = "JSON content is invalid"
        elif ext == ".csv":
            error = _csv_validate(content, limits["max_csv_rows"])
        else:
            if b"\x00" in content[:8192]:
                error = "Text document appears to contain binary content"
            else:
                try:
                    content.decode("utf-8-sig")
                    error = None
                except UnicodeDecodeError:
                    error = "Text documents must use UTF-8 encoding"
        return (error is None), error
    except Exception as exc:
        file.seek(0)
        return False, f"Content validation failed ({type(exc).__name__})"


def validate_upload_limits(filename: str, mime_type: str, file_size: int, run_file_count: int = 0) -> Tuple[bool, Optional[str]]:
    limits = get_evidence_limits()
    if file_size > limits["max_upload_bytes"]:
        return False, f"File exceeds the configured {limits['max_upload_mb']} MB upload limit"
    if file_size == 0:
        return False, "Empty files are not allowed"
    if run_file_count >= limits["max_files_per_run"]:
        return False, f"Run has reached maximum of {limits['max_files_per_run']} files"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' not allowed"
    if mime_type not in MIME_BY_EXTENSION[ext]:
        return False, "Declared MIME type does not match the file extension"
    return True, None


class EvidenceSecurityValidator:
    """Apply filename, configured limits, content type and parser safety checks."""

    def __init__(self):
        self.limits = get_evidence_limits()

    def validate_upload(self, file: BinaryIO, filename: str, mime_type: str, file_size: int,
                        run_file_count: int = 0) -> Tuple[bool, Optional[str], dict]:
        details = {"filename": filename, "mime_type": mime_type, "file_size": file_size, "checks": {}}
        if not filename or len(filename) > 255 or any(ord(char) < 32 for char in filename):
            details["checks"]["filename"] = "FAILED"
            return False, "Filename is empty, too long, or contains control characters", details
        details["checks"]["filename"] = "PASSED"
        if check_path_traversal(filename):
            details["checks"]["path_traversal"] = "FAILED"
            return False, "Filename contains a path traversal attempt", details
        details["checks"]["path_traversal"] = "PASSED"
        valid, error = validate_upload_limits(filename, mime_type, file_size, run_file_count)
        if not valid:
            details["checks"]["limits"] = "FAILED"
            return False, error, details
        details["checks"]["limits"] = "PASSED"
        valid, error = validate_file_content(file, filename, mime_type)
        if not valid:
            details["checks"]["content_validation"] = "FAILED"
            return False, error, details
        details["checks"]["content_validation"] = "PASSED"
        details["sha256"] = compute_file_hash(file)
        return True, None, details

    def scan_for_prompt_injection(self, text: str) -> dict:
        has_injection, patterns = detect_prompt_injection(text)
        return {"has_prompt_injection": has_injection, "detected_patterns": patterns, "text_length": len(text)}

    def validate_pdf_safety(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        try:
            error = _pdf_validate(file_path.read_bytes(), self.limits["max_pdf_pages"])
            return error is None, error
        except OSError:
            return False, "PDF could not be read"
