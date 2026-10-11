"""Vector store abstraction for evidence RAG."""

from __future__ import annotations

import os
from pathlib import Path
import uuid
import numpy as np
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_chunks(
        self,
        run_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """Add chunks with embeddings to the store."""
        pass

    @abstractmethod
    def search(
        self,
        run_id: str,
        query_embedding: List[float],
        top_k: int,
        evidence_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        pass

    @abstractmethod
    def delete_run(self, run_id: str) -> None:
        """Delete all data for a run."""
        pass

    @abstractmethod
    def delete_evidence(self, run_id: str, evidence_id: str) -> None:
        """Delete all vectors for a specific evidence item."""
        pass

    @abstractmethod
    def get_chunk_count(self, run_id: str) -> int:
        """Get the number of chunks for a run."""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB-based vector store."""

    def __init__(self, persist_dir: Optional[str] = None):
        import chromadb
        from chromadb.config import Settings

        project_root = Path(__file__).resolve().parents[2]
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR") or str(project_root / "data" / "chroma")
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

    def _get_collection_name(self, run_id: str) -> str:
        """Get collection name for a run (namespaced)."""
        return f"evidence_{run_id}"

    def add_chunks(
        self,
        run_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        if not chunks:
            return

        collection_name = self._get_collection_name(run_id)
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"run_id": run_id},
        )

        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        # Chroma metadata values must be scalar strings, numbers, or booleans;
        # `None` is not a valid MetadataValue. Omit absent fields such as the
        # section for page-based PDF chunks.
        metadatas = [
            {
                key: value
                for key, value in {
                    "evidence_id": chunk["evidence_id"],
                    "run_id": chunk["run_id"],
                    "filename": chunk["filename"],
                    "page": chunk.get("page"),
                    "section": chunk.get("section"),
                    "chunk_index": chunk.get("chunk_index"),
                    "created_at": chunk.get("created_at"),
                }.items()
                if value is not None
            }
            for chunk in chunks
        ]

        # Upsert makes a processing retry safe if an earlier attempt wrote
        # some chunks before failing.
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        run_id: str,
        query_embedding: List[float],
        top_k: int,
        evidence_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        collection_name = self._get_collection_name(run_id)
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            return []

        query_options = {}
        if evidence_ids is not None:
            if not evidence_ids:
                return []
            query_options["where"] = {"evidence_id": {"$in": evidence_ids}}
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances", "embeddings"],
            **query_options,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        matches = []
        for i in range(len(results["ids"][0])):
            stored_embedding = results["embeddings"][0][i]
            query_vector = np.asarray(query_embedding, dtype=float)
            stored_vector = np.asarray(stored_embedding, dtype=float)
            denominator = float(np.linalg.norm(query_vector) * np.linalg.norm(stored_vector))
            cosine_similarity = (
                float(np.dot(query_vector, stored_vector) / denominator)
                if denominator
                else 0.0
            )
            matches.append({
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "score": cosine_similarity,
            })

        return matches

    def delete_run(self, run_id: str) -> None:
        collection_name = self._get_collection_name(run_id)
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass

    def delete_evidence(self, run_id: str, evidence_id: str) -> None:
        """Delete all vectors for a specific evidence item."""
        collection_name = self._get_collection_name(run_id)
        if collection_name not in {getattr(item, "name", item) for item in self.client.list_collections()}:
            return
        collection = self.client.get_collection(name=collection_name)
        # Query for all chunks belonging to this evidence and surface failures
        # so lifecycle deletion can report an incomplete vector cleanup.
        results = collection.get(where={"evidence_id": evidence_id}, include=["metadatas"])
        if results["ids"]:
            collection.delete(ids=results["ids"])

    def get_chunk_count(self, run_id: str) -> int:
        collection_name = self._get_collection_name(run_id)
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0


class InMemoryVectorStore(VectorStore):
    """Small process-local vector store for serverless deployments.

    Vercel functions do not provide durable local storage. This fallback keeps
    evidence retrieval functional within a warm invocation without importing
    the much larger ChromaDB dependency.
    """

    def __init__(self) -> None:
        self._chunks: dict[str, dict[str, dict[str, Any]]] = {}

    def add_chunks(
        self,
        run_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        run_chunks = self._chunks.setdefault(run_id, {})
        for chunk, embedding in zip(chunks, embeddings):
            run_chunks[chunk["chunk_id"]] = {
                "chunk": chunk,
                "embedding": embedding,
            }

    def search(
        self,
        run_id: str,
        query_embedding: List[float],
        top_k: int,
        evidence_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        query = np.asarray(query_embedding, dtype=float)
        allowed = set(evidence_ids) if evidence_ids is not None else None
        matches: list[dict[str, Any]] = []
        for item in self._chunks.get(run_id, {}).values():
            chunk = item["chunk"]
            if allowed is not None and chunk["evidence_id"] not in allowed:
                continue
            stored = np.asarray(item["embedding"], dtype=float)
            denominator = float(np.linalg.norm(query) * np.linalg.norm(stored))
            score = float(np.dot(query, stored) / denominator) if denominator else 0.0
            matches.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "metadata": {
                    key: value for key, value in {
                        "evidence_id": chunk["evidence_id"],
                        "run_id": chunk["run_id"],
                        "filename": chunk["filename"],
                        "page": chunk.get("page"),
                        "section": chunk.get("section"),
                    }.items() if value is not None
                },
                "distance": 1.0 - score,
                "score": score,
            })
        return sorted(matches, key=lambda item: item["score"], reverse=True)[:top_k]

    def delete_run(self, run_id: str) -> None:
        self._chunks.pop(run_id, None)

    def delete_evidence(self, run_id: str, evidence_id: str) -> None:
        run_chunks = self._chunks.get(run_id, {})
        for chunk_id in [
            key for key, value in run_chunks.items()
            if value["chunk"]["evidence_id"] == evidence_id
        ]:
            del run_chunks[chunk_id]

    def get_chunk_count(self, run_id: str) -> int:
        return len(self._chunks.get(run_id, {}))


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        if os.getenv("VERCEL"):
            _vector_store = InMemoryVectorStore()
        else:
            try:
                _vector_store = ChromaVectorStore()
            except ImportError:
                _vector_store = InMemoryVectorStore()
    return _vector_store
