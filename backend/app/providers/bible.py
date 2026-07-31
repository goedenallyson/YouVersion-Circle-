"""Bible content providers.

- LocalBibleProvider: reads a JSON corpus shipped in data/ (public-domain
  WEB translation by default). Zero external dependencies, runs anywhere.
- YouVersionBibleProvider / ApiBibleProvider: HTTP-backed, gated behind
  verified partner credentials.

Reference parsing is deliberately small and testable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from app.core.config import Settings
from app.models.schemas import ScriptureChunk, VerseRef
from app.providers.base import BibleContentProvider

_REF_RE = re.compile(
    r"^\s*(?P<book>(?:[1-3]\s+)?[A-Za-z ]+?)\s+"
    r"(?P<chapter>\d+):(?P<start>\d+)(?:-(?P<end>\d+))?\s*$"
)


def parse_reference(reference: str) -> tuple[str, int, int, int | None]:
    m = _REF_RE.match(reference)
    if not m:
        raise ValueError(f"Unparseable reference: {reference!r}")
    end = int(m["end"]) if m["end"] else None
    return m["book"].strip(), int(m["chapter"]), int(m["start"]), end


class LocalBibleProvider(BibleContentProvider):
    name = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_dir = settings.data_path

    def _corpus_path(self, translation: str) -> Path:
        return self.data_dir / f"{translation.lower()}.json"

    def load_translation(self, translation: str) -> list[ScriptureChunk]:
        path = self._corpus_path(translation)
        if not path.exists():
            raise FileNotFoundError(
                f"No local corpus at {path}. Run scripts/fetch_bible.py or "
                f"place a {translation}.json verse file there."
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        chunks: list[ScriptureChunk] = []
        for v in raw["verses"]:
            ref = VerseRef(
                translation=translation,
                book=v["book"],
                chapter=int(v["chapter"]),
                verse=int(v["verse"]),
            )
            chunks.append(
                ScriptureChunk(
                    id=f"{translation}:{v['book']}:{v['chapter']}:{v['verse']}",
                    text=v["text"].strip(),
                    ref=ref,
                )
            )
        return chunks

    def passage(self, translation: str, reference: str) -> list[ScriptureChunk]:
        book, chapter, start, end = parse_reference(reference)
        end = end or start
        all_chunks = self.load_translation(translation)
        return [
            c
            for c in all_chunks
            if c.ref.book.lower() == book.lower()
            and c.ref.chapter == chapter
            and start <= c.ref.verse <= end
        ]


class ApiBibleProvider(BibleContentProvider):
    """scripture.api.bible-backed provider (licensed fallback to YouVersion).

    Gated: requires BIBLE_API_KEY + BIBLE_BASE_URL. Kept minimal; expand the
    response mapping against the live API when credentials are available.
    """

    name = "apibible"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not (settings.bible_api_key and settings.bible_base_url):
            raise RuntimeError("ApiBibleProvider requires BIBLE_API_KEY/BASE_URL.")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.settings.bible_base_url,
            headers={"api-key": self.settings.bible_api_key},
            timeout=30,
        )

    def load_translation(self, translation: str) -> list[ScriptureChunk]:
        raise NotImplementedError(
            "Bulk load over HTTP is disabled to respect rate limits/licensing. "
            "Index from a local export; use passage() for on-demand lookups."
        )

    def passage(self, translation: str, reference: str) -> list[ScriptureChunk]:
        book, chapter, start, end = parse_reference(reference)
        end = end or start
        # Endpoint shape is provider-specific; confirm against live docs.
        with self._client() as client:
            resp = client.get(
                "/verses",
                params={"reference": reference, "translation": translation},
            )
            resp.raise_for_status()
            payload = resp.json()
        chunks: list[ScriptureChunk] = []
        for v in payload.get("verses", []):
            chunks.append(
                ScriptureChunk(
                    id=f"{translation}:{book}:{chapter}:{v['verse']}",
                    text=v["text"].strip(),
                    ref=VerseRef(
                        translation=translation,
                        book=book,
                        chapter=chapter,
                        verse=int(v["verse"]),
                    ),
                )
            )
        return chunks
