"""Central configuration.

All secrets/URLs come from environment variables so the same code runs
locally, in a Kaggle notebook, or in a deployed container. Nothing here
hard-codes a provider spec we haven't verified.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    """Resolve the repo root regardless of the current working directory.

    Data lives at the repo root (``data/``) while the app is often launched
    from ``backend/`` (tests, uvicorn) or from a Kaggle notebook. Anchoring
    relative data paths here keeps everything working from any CWD.

    Walks up from this file looking for a directory that contains ``data/``
    or a ``.git`` folder; falls back to the current working directory.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").is_dir() or (parent / ".git").is_dir():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "scripture-in-new-frontiers"
    environment: str = Field(default="local")  # local | kaggle | prod
    log_level: str = Field(default="INFO")

    # --- Gloo AI (values-aligned LLM). Real base URL/model filled in when
    #     the project manager provides verified API docs/keys. ---
    gloo_api_key: str | None = None
    gloo_base_url: str | None = None
    gloo_model: str = "gloo-360-ai"
    gloo_client_id: str | None = None
    gloo_client_secret: str | None = None
    gloo_tradition: str | None = None  # evangelical | catholic | mainline | None

    # --- Data ---
    data_dir: str = Field(default="data/raw")

    # --- Bible content (YouVersion partner API, or a licensed fallback
    #     source such as scripture.api.bible). ---
    bible_provider: str = Field(default="local")  # local | youversion | apibible
    bible_api_key: str | None = None  # YouVersion App Key (X-YVP-App-Key)
    bible_base_url: str = "https://developers.youversion.com/api"
    bible_default_translation: str = "WEB"  # local seed; YV uses version ids like BSB

    # --- Embeddings / vector store ---
    embedding_provider: str = Field(default="local")  # local | gloo | openai
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_path: str = "data/index"
    top_k: int = 6

    # --- Generation guardrails ---
    max_context_chunks: int = 8
    require_citations: bool = True


    def resolve_path(self, value: str) -> Path:
        """Resolve a possibly-relative data path against the repo root."""
        p = Path(value)
        return p if p.is_absolute() else project_root() / p

    @property
    def data_path(self) -> Path:
        return self.resolve_path(self.data_dir)

    @property
    def vector_store_dir(self) -> Path:
        return self.resolve_path(self.vector_store_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
