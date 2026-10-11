"""Embedding provider abstraction for evidence RAG."""

from __future__ import annotations

import os
import hashlib
import re
import math
from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers.

    This is a development/fallback option that doesn't require external APIs.
    """

    def __init__(self, model_name: str = "local-hash-v1"):
        self._model_name = model_name
        self._model = None
        self._dimension = 384  # all-MiniLM-L6-v2 dimension

    def _load_model(self):
        """Lazily load the model."""
        if self._model is None:
            if self._model_name == "local-hash-v1":
                self._model = False
                return
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                self._model = False

    def _hash_embedding(self, text: str) -> List[float]:
        vector = [0.0] * self._dimension
        tokens = re.findall(r"[\w.-]+", text.casefold())
        features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self._dimension
            vector[index] += 1.0 if number & (1 << 63) else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if self._model is False:
            return [self._hash_embedding(text) for text in texts]
        embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        self._load_model()
        if self._model is False:
            return self._hash_embedding(text)
        embedding = self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


class NVIDIAEmbeddingProvider(EmbeddingProvider):
    """NVIDIA embedding provider using NVIDIA's embedding API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "nvidia/embed-qa-4",
        timeout: float = 30.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._dimension = 1024  # Typical for NVIDIA embeddings

    def embed(self, texts: List[str]) -> List[List[float]]:
        import httpx

        embeddings = []
        # Process in batches to avoid large payloads
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            batch_embeddings = self._embed_batch(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        import httpx

        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model


# Provider registry
_PROVIDERS = {
    "local": LocalEmbeddingProvider,
    "nvidia": NVIDIAEmbeddingProvider,
}


def get_embedding_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> EmbeddingProvider:
    """Get an embedding provider instance.

    Configuration via environment variables:
    - EMBEDDING_PROVIDER: "local" or "nvidia" (default: "local")
    - EMBEDDING_MODEL: model name (provider-specific)
    - For NVIDIA: NVIDIA_API_KEY, NVIDIA_BASE_URL
    """
    from app.core.config import get_settings
    settings = get_settings()
    provider = provider or os.getenv("EMBEDDING_PROVIDER", settings.embedding_provider).lower()
    model = model or os.getenv("EMBEDDING_MODEL") or settings.embedding_model

    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown embedding provider: {provider}. Available: {list(_PROVIDERS.keys())}")

    provider_class = _PROVIDERS[provider]

    if provider == "nvidia":
        api_key = settings.nvidia_api_key or os.getenv("NVIDIA_API_KEY")
        base_url = settings.nvidia_base_url or os.getenv("NVIDIA_BASE_URL")
        if not api_key or not base_url:
            raise RuntimeError("NVIDIA_API_KEY and NVIDIA_BASE_URL required for NVIDIA provider")
        return provider_class(api_key=api_key, base_url=base_url, model=model or "nvidia/embed-qa-4")
    else:
        return provider_class(model_name=model or "local-hash-v1")
