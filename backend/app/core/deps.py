"""Dependency wiring — the single place providers are selected by config."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.providers.base import BibleContentProvider, EmbeddingProvider, LLMProvider
from app.providers.bible import ApiBibleProvider, LocalBibleProvider
from app.providers.embeddings import LocalEmbeddingProvider
from app.providers.gloo import GlooLLMProvider
from app.providers.youversion import YouVersionBibleProvider
from app.rag.engine import RagEngine
from app.rag.circle import CircleEngine
from app.rag.vector_store import VectorStore


def _bible_provider(s: Settings) -> BibleContentProvider:
    if s.bible_provider == "youversion" and s.bible_api_key:
        try:
            return YouVersionBibleProvider(s)
        except RuntimeError:
            return LocalBibleProvider(s)
    if s.bible_provider == "apibible":
        return ApiBibleProvider(s)
    return LocalBibleProvider(s)


def _embedder(s: Settings) -> EmbeddingProvider:
    return LocalEmbeddingProvider(s)


def _llm(s: Settings) -> LLMProvider | None:
    provider = GlooLLMProvider(s)
    return provider


@lru_cache
def get_engine() -> RagEngine:
    s = get_settings()
    return RagEngine(
        settings=s,
        bible=_bible_provider(s),
        index_source=LocalBibleProvider(s),
        embedder=_embedder(s),
        store=VectorStore(str(s.vector_store_dir)),
        llm=_llm(s),
    )


@lru_cache
def get_circle_engine() -> CircleEngine:
    return CircleEngine(get_engine())
