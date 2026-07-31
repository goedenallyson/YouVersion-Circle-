"""Abstract provider interfaces.

These define the *contract*. Concrete Gloo / YouVersion implementations
slot in behind them once verified API specs and credentials are supplied,
without touching the RAG core or API layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import ScriptureChunk


class LLMProvider(ABC):
    """A chat/completion provider (e.g., Gloo 360 AI values-aligned LLM)."""

    name: str = "base-llm"

    @abstractmethod
    def generate(
        self,
        *,
        system: str,
        prompt: str,
        context: list[ScriptureChunk],
        temperature: float = 0.2,
    ) -> str:
        ...


class EmbeddingProvider(ABC):
    """Turns text into vectors for semantic retrieval."""

    name: str = "base-embed"
    dim: int = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class BibleContentProvider(ABC):
    """Supplies scripture text (YouVersion partner API or licensed fallback)."""

    name: str = "base-bible"

    @abstractmethod
    def load_translation(self, translation: str) -> list[ScriptureChunk]:
        """Return all verse-level chunks for a translation (for indexing)."""

    @abstractmethod
    def passage(self, translation: str, reference: str) -> list[ScriptureChunk]:
        """Fetch a specific passage by reference string, e.g. 'John 3:16-17'."""
