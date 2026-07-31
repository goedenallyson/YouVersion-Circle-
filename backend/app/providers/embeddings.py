"""Embedding providers.

LocalEmbeddingProvider tries sentence-transformers; if unavailable it falls
back to a deterministic hashing embedding so tests and demos still run with
no heavy dependencies. Swap in a Gloo/OpenAI embedding provider by
implementing EmbeddingProvider.
"""
from __future__ import annotations

import hashlib
import math

from app.core.config import Settings
from app.providers.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    name = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        try:  # optional heavy dependency
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.embedding_model)
            self.dim = self._model.get_sentence_embedding_dimension()
            self.name = f"st:{settings.embedding_model}"
        except Exception:
            self.dim = 256  # hashing fallback dimensionality
            self.name = "hashing-fallback"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is not None:
            return self._model.encode(
                texts, normalize_embeddings=True
            ).tolist()
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        """Deterministic bag-of-hashed-tokens vector, L2-normalized."""
        vec = [0.0] * self.dim
        for token in text.lower().split():
            h = int(hashlib.sha1(token.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
