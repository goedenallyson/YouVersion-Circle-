"""YouVersion Platform API provider.

Verified against developers.youversion.com (2026-07):
  - Auth header: X-YVP-App-Key
  - Base: https://developers.youversion.com/api
  - Passages endpoint returns Bible text for a verse/passage/chapter
  - Bible collection lists licensed versions available to the app
  - Pagination via page_size / page_token -> next_page_token

Activates only when BIBLE_API_KEY is set; otherwise the app uses the local
public-domain corpus so everything runs offline.
"""
from __future__ import annotations

import httpx

from app.core.config import Settings
from app.models.schemas import ScriptureChunk, VerseRef
from app.providers.base import BibleContentProvider
from app.providers.bible import parse_reference


class YouVersionBibleProvider(BibleContentProvider):
    name = "youversion"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.bible_api_key:
            raise RuntimeError(
                "YouVersionBibleProvider requires BIBLE_API_KEY (App Key)."
            )
        self.base_url = settings.bible_base_url.rstrip("/")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers={
                "X-YVP-App-Key": self.settings.bible_api_key,
                "accept": "application/json",
            },
            timeout=30,
        )

    @property
    def configured(self) -> bool:
        return True

    def list_versions(self) -> list[dict]:
        """Get the Bible collection available to this app (licensed versions)."""
        versions: list[dict] = []
        page_token: str | None = None
        with self._client() as client:
            while True:
                params = {"page_size": 100}
                if page_token:
                    params["page_token"] = page_token
                resp = client.get("/bibles", params=params)
                resp.raise_for_status()
                data = resp.json()
                versions.extend(data.get("data", data.get("bibles", [])))
                page_token = data.get("next_page_token")
                if not page_token:
                    break
        return versions

    def passage(self, translation: str, reference: str) -> list[ScriptureChunk]:
        """Fetch a passage, e.g. passage('BSB', 'John 3:16-17')."""
        book, chapter, start, end = parse_reference(reference)
        end = end or start
        with self._client() as client:
            resp = client.get(
                f"/bibles/{translation}/passages",
                params={"reference": reference},
            )
            resp.raise_for_status()
            payload = resp.json()

        chunks: list[ScriptureChunk] = []
        verses = payload.get("verses") or payload.get("data", {}).get("verses", [])
        if verses:
            for v in verses:
                vnum = int(v.get("verse", v.get("number", start)))
                chunks.append(
                    ScriptureChunk(
                        id=f"{translation}:{book}:{chapter}:{vnum}",
                        text=(v.get("text") or v.get("content", "")).strip(),
                        ref=VerseRef(
                            translation=translation,
                            book=book,
                            chapter=chapter,
                            verse=vnum,
                        ),
                    )
                )
        else:
            # Some responses return a single rendered passage string.
            text = (payload.get("content") or payload.get("text") or "").strip()
            if text:
                chunks.append(
                    ScriptureChunk(
                        id=f"{translation}:{book}:{chapter}:{start}",
                        text=text,
                        ref=VerseRef(
                            translation=translation,
                            book=book,
                            chapter=chapter,
                            verse=start,
                        ),
                        end_verse=end,
                    )
                )
        return chunks

    def load_translation(self, translation: str) -> list[ScriptureChunk]:
        raise NotImplementedError(
            "Bulk-loading a full translation over the API is disabled to "
            "respect rate limits and licensing. Index from a local export "
            "and use passage() for on-demand, always-fresh lookups."
        )
