"""RAG engine: retrieval + grounded, cited generation.

Ties the providers together. Includes a grounding check and a deterministic
fallback answer path so the system degrades gracefully when no LLM is
configured (useful for CI, Kaggle offline runs, and demos).
"""
from __future__ import annotations

from app.core.config import Settings
from app.models.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    ScriptureChunk,
)
from app.providers.base import (
    BibleContentProvider,
    EmbeddingProvider,
    LLMProvider,
)
from app.rag.vector_store import VectorStore

SYSTEM_PROMPT = (
    "You are a careful, values-aligned scripture assistant. Answer only from "
    "the provided passages. Always cite references in brackets. Be honest "
    "about uncertainty. Do not invent verses or add doctrine beyond the text."
)


class RagEngine:
    def __init__(
        self,
        *,
        settings: Settings,
        bible: BibleContentProvider,
        embedder: EmbeddingProvider,
        store: VectorStore,
        llm: LLMProvider | None = None,
        index_source: BibleContentProvider | None = None,
    ) -> None:
        self.settings = settings
        self.bible = bible
        # Source used to build the vector index (bulk load); defaults to the
        # live provider but is usually a local corpus provider.
        self.index_source = index_source or bible
        self.embedder = embedder
        self.store = store
        self.llm = llm

    # --- Indexing ---
    def build_index(self, translation: str) -> int:
        chunks = self.index_source.load_translation(translation)
        vectors = self.embedder.embed([c.text for c in chunks])
        self.store.build(chunks, vectors)
        self.store.save()
        return self.store.size

    def ensure_index(self, translation: str) -> None:
        if self.store.size == 0 and not self.store.load():
            self.build_index(translation)

    # --- Retrieval ---
    def search(self, query: str, top_k: int | None = None) -> list[ScriptureChunk]:
        k = top_k or self.settings.top_k
        # Guarantee an index exists (default translation) before searching.
        self.ensure_index(self.settings.bible_default_translation)
        qvec = self.embedder.embed([query])[0]
        return self.store.search(qvec, k)

    # --- Ask (retrieval-augmented generation) ---
    def ask(self, req: AskRequest) -> AskResponse:
        translation = req.translation or self.settings.bible_default_translation
        self.ensure_index(translation)
        chunks = self.search(req.question, req.top_k)
        grounded = len(chunks) > 0

        if self.llm is not None and getattr(self.llm, "configured", True):
            answer = self.llm.generate(
                system=SYSTEM_PROMPT,
                prompt=req.question,
                context=chunks[: self.settings.max_context_chunks],
            )
            model = self.llm.name
        else:
            answer = self._extractive_answer(req.question, chunks)
            model = "extractive-fallback"

        return AskResponse(
            answer=answer,
            citations=[
                Citation(citation=c.citation, text=c.text, score=c.score)
                for c in chunks
            ],
            model=model,
            grounded=grounded,
        )

    def _extractive_answer(
        self, question: str, chunks: list[ScriptureChunk]
    ) -> str:
        if not chunks:
            return (
                "I couldn't find scripture passages relevant to that question "
                "in the indexed translation."
            )
        top = chunks[: min(3, len(chunks))]
        body = " ".join(f"{c.text} [{c.citation}]" for c in top)
        return (
            f"Based on the most relevant passages: {body}"
        )
