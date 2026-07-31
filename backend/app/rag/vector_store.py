"""A tiny, dependency-light vector store.

Uses numpy for cosine similarity over an in-memory matrix, persisted to
disk as .npy + .jsonl. This is intentionally simple and swappable for FAISS
or a hosted vector DB behind the same interface if scale demands it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.models.schemas import ScriptureChunk


class VectorStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._matrix: np.ndarray | None = None
        self._chunks: list[ScriptureChunk] = []

    @property
    def size(self) -> int:
        return len(self._chunks)

    def build(self, chunks: list[ScriptureChunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        self._chunks = chunks
        self._matrix = np.asarray(vectors, dtype=np.float32)

    def save(self) -> None:
        if self._matrix is None:
            raise RuntimeError("Nothing to save; build the index first.")
        np.save(self.path / "vectors.npy", self._matrix)
        with (self.path / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self._chunks:
                f.write(c.model_dump_json() + "\n")

    def load(self) -> bool:
        vpath = self.path / "vectors.npy"
        cpath = self.path / "chunks.jsonl"
        if not (vpath.exists() and cpath.exists()):
            return False
        self._matrix = np.load(vpath)
        self._chunks = [
            ScriptureChunk.model_validate_json(line)
            for line in cpath.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return True

    def search(self, query_vec: list[float], top_k: int) -> list[ScriptureChunk]:
        if self._matrix is None or not self._chunks:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        qn = np.linalg.norm(q) or 1.0
        mn = np.linalg.norm(self._matrix, axis=1)
        mn[mn == 0] = 1.0
        sims = (self._matrix @ q) / (mn * qn)
        idx = np.argsort(-sims)[:top_k]
        results: list[ScriptureChunk] = []
        for i in idx:
            c = self._chunks[int(i)].model_copy()
            c.score = float(sims[int(i)])
            results.append(c)
        return results
