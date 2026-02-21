from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache

import httpx
import numpy as np
from fastembed import SparseTextEmbedding

from agent.embedder.config import BATCH_SIZE, DENSE_DIM, SPARSE_MODEL
from agent.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SparseVector:
    indices: list[int]
    values: list[float]


@dataclass
class EmbedderService:
    _sparse_model: SparseTextEmbedding = field(init=False)
    _client: httpx.AsyncClient = field(init=False)

    def __post_init__(self) -> None:
        self._sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info("EmbedderService initialized (sparse=%s)", SPARSE_MODEL)

    async def embed_texts(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[SparseVector]]:
        dense = await self._dense_embed(texts)
        sparse = self._sparse_embed(texts)
        return dense, sparse

    async def _dense_embed(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        url = f"{settings.embed_base_url}/api/embed"
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            resp = await self._client.post(
                url,
                json={
                    "model": settings.embed_model,
                    "input": batch,
                    "truncate": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data["embeddings"]

            for emb in embeddings:
                vec = np.array(emb, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                assert len(vec) == DENSE_DIM, f"Expected {DENSE_DIM}, got {len(vec)}"
                all_embeddings.append(vec.tolist())

        return all_embeddings

    def _sparse_embed(self, texts: list[str]) -> list[SparseVector]:
        results: list[SparseVector] = []
        for emb in self._sparse_model.embed(texts, batch_size=BATCH_SIZE):
            results.append(
                SparseVector(
                    indices=emb.indices.tolist(),
                    values=emb.values.tolist(),
                )
            )
        return results

    async def embed_query(self, text: str) -> tuple[list[float], SparseVector]:
        dense, sparse = await self.embed_texts([text])
        return dense[0], sparse[0]


@lru_cache(maxsize=1)
def get_embedder() -> EmbedderService:
    return EmbedderService()
