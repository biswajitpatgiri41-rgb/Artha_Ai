"""Text chunking for evidence documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import List, Optional

from app.evidence.schemas import EvidenceDocument, EvidenceFormat


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    chunk_size: int = int(os.getenv("EVIDENCE_CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("EVIDENCE_CHUNK_OVERLAP", "200"))
    min_chunk_size: int = int(os.getenv("EVIDENCE_MIN_CHUNK_SIZE", "100"))


def chunk_text(text: str, config: Optional[ChunkConfig] = None) -> List[str]:
    """Split text into overlapping chunks.

    Args:
        text: The text to chunk
        config: Chunking configuration

    Returns:
        List of text chunks
    """
    if config is None:
        config = ChunkConfig()
    if config.chunk_size <= 0 or config.chunk_overlap < 0 or config.chunk_overlap >= config.chunk_size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than chunk size")

    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + config.chunk_size, text_len)

        # Try to break at a sentence boundary
        if end < text_len:
            # Look for sentence endings near the end
            for i in range(end, max(start + config.min_chunk_size, end - 200), -1):
                if text[i] in ".!?":
                    end = i + 1
                    break

        chunk = text[start:end].strip()
        if len(chunk) >= config.min_chunk_size and chunk.strip():
            chunks.append(chunk)

        if end >= text_len:
            break

        start = end - config.chunk_overlap

    return chunks


def chunk_document(doc: EvidenceDocument, config: Optional[ChunkConfig] = None) -> List[dict]:
    """Chunk an EvidenceDocument based on its format.

    Returns list of chunks with metadata:
    - For PDF: page number, chunk index, text
    - For TXT/MD: single "page", chunk index, text
    """
    if config is None:
        config = ChunkConfig()

    chunks = []
    created_at = datetime.now(timezone.utc).isoformat()

    if doc.format in (EvidenceFormat.PDF,):
        # Chunk per page for PDFs
        if doc.pages:
            for page_info in doc.pages:
                page_num = page_info.get("page", 1)
                page_text = page_info.get("text", "")
                page_chunks = chunk_text(page_text, config)
                for chunk_idx, chunk in enumerate(page_chunks):
                    chunks.append({
                        "chunk_id": f"{doc.evidence_id}_p{page_num}_c{chunk_idx}",
                        "evidence_id": doc.evidence_id,
                        "run_id": doc.run_id,
                        "filename": doc.filename,
                        "page": page_num,
                        "section": None,
                        "text": chunk,
                        "chunk_index": chunk_idx,
                        "created_at": created_at,
                    })
    elif doc.format in (EvidenceFormat.TXT, EvidenceFormat.MD):
        # Preserve Markdown section headings when supplied by the parser.
        pages = doc.pages or [{"page": 1, "text": doc.text or "", "section": None}]
        chunk_idx = 0
        for page_info in pages:
            for chunk in chunk_text(page_info.get("text", ""), config):
                if not chunk.strip():
                    continue
                chunks.append({
                    "chunk_id": f"{doc.evidence_id}_c{chunk_idx}",
                    "evidence_id": doc.evidence_id,
                    "run_id": doc.run_id,
                    "filename": doc.filename,
                    "page": page_info.get("page", 1),
                    "section": page_info.get("section"),
                    "text": chunk,
                    "chunk_index": chunk_idx,
                    "created_at": created_at,
                })
                chunk_idx += 1

    # Note: CSV, XLSX, JSON are not chunked for vector storage
    # They use structured evidence tools instead

    return chunks
