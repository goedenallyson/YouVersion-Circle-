"""Gloo AI Studio provider (Completions V2).

Verified against docs.gloo.com (2026-07):
  - OAuth2 client-credentials -> short-lived bearer token (expires_in ~3600s)
  - POST https://platform.ai.gloo.com/ai/v2/chat/completions
  - Body: {messages, auto_routing, model|model_family, tradition, stream}
  - Values-aligned / faith-tuned; 6-dimension AI safety; `tradition` steering.

Network calls activate only when GLOO_CLIENT_ID + GLOO_CLIENT_SECRET are set.
Without them, `.configured` is False and the RAG engine uses its extractive
fallback so the whole system still runs offline (CI, Kaggle, demos).
"""
from __future__ import annotations

import time

import httpx

from app.core.config import Settings
from app.models.schemas import ScriptureChunk
from app.providers.base import LLMProvider

# Gloo OAuth + inference endpoints (from verified developer docs).
GLOO_TOKEN_URL = "https://platform.ai.gloo.com/oauth2/token"
GLOO_COMPLETIONS_URL = "https://platform.ai.gloo.com/ai/v2/chat/completions"


class GlooLLMProvider(LLMProvider):
    name = "gloo-ai-studio"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._configured = bool(
            settings.gloo_client_id and settings.gloo_client_secret
        )
        self._token: str | None = None
        self._token_expiry: float = 0.0
        # Optional theological steering, e.g. "evangelical" | "catholic" | "mainline".
        self.tradition = getattr(settings, "gloo_tradition", None)

    @property
    def configured(self) -> bool:
        return self._configured

    # --- OAuth2 client-credentials, with in-memory token caching ---
    def _get_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry - 60:
            return self._token
        resp = httpx.post(
            GLOO_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.settings.gloo_client_id, self.settings.gloo_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expiry = now + int(payload.get("expires_in", 3600))
        return self._token

    def _build_messages(
        self, system: str, prompt: str, context: list[ScriptureChunk]
    ) -> list[dict]:
        context_block = "\n\n".join(f"[{c.citation}] {c.text}" for c in context)
        user = (
            f"{prompt}\n\n"
            "Ground your response ONLY in the scripture passages below. "
            "Cite each reference in brackets. If they do not address the "
            f"question, say so plainly.\n\n=== SCRIPTURE ===\n{context_block}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        context: list[ScriptureChunk],
        temperature: float = 0.2,
    ) -> str:
        if not self._configured:
            raise RuntimeError(
                "GlooLLMProvider not configured. Set GLOO_CLIENT_ID and "
                "GLOO_CLIENT_SECRET from Gloo AI Studio API Credentials."
            )
        body: dict = {
            "messages": self._build_messages(system, prompt, context),
            "auto_routing": True,  # AI Core: Gloo picks the best model tier
            "stream": False,
            "temperature": temperature,
        }
        if self.tradition:
            body["tradition"] = self.tradition

        resp = httpx.post(
            GLOO_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
                "accept": "application/json",
            },
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Completions V2 returns an OpenAI-compatible chat envelope.
        return data["choices"][0]["message"]["content"].strip()

    # Convenience: free-form generation (no retrieval context), used by the
    # contextual "framing" layer that wraps a verse for the moment.
    def frame(self, system: str, prompt: str, temperature: float = 0.4) -> str:
        if not self._configured:
            raise RuntimeError("GlooLLMProvider not configured.")
        body: dict = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "auto_routing": True,
            "stream": False,
            "temperature": temperature,
        }
        if self.tradition:
            body["tradition"] = self.tradition
        resp = httpx.post(
            GLOO_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
