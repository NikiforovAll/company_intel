from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    NamedSparseVector,
    NamedVector,
    PayloadSchemaType,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from agent.chunker.models import Chunk
from agent.embedder.pipeline import SparseVector as EmbedSparseVector
from agent.settings import get_settings
from agent.vectorstore.config import (
    COLLECTION_NAME,
    DENSE_DIM,
    DENSE_SCORE_THRESHOLD,
    DENSE_VECTOR_NAME,
    SEARCH_DENSE_LIMIT,
    SEARCH_FUSION_LIMIT,
    SEARCH_SPARSE_LIMIT,
    SPARSE_VECTOR_NAME,
    UPSERT_BATCH_SIZE,
)

logger = logging.getLogger(__name__)


@dataclass
class VectorStoreService:
    _client: QdrantClient = field(init=False)

    def __post_init__(self) -> None:
        settings = get_settings()
        self._client = QdrantClient(
            url=settings.qdrant_endpoint,
            api_key=settings.qdrant_api_key,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self._client.get_collections().collections]
        if COLLECTION_NAME in collections:
            return

        self._client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                DENSE_VECTOR_NAME: VectorParams(
                    size=DENSE_DIM, distance=Distance.COSINE
                ),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: SparseVectorParams(),
            },
        )

        self._client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="company",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="source_type",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Created Qdrant collection '%s'", COLLECTION_NAME)

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[EmbedSparseVector],
    ) -> int:
        points: list[PointStruct] = []
        for chunk, dense, sparse in zip(
            chunks, dense_vectors, sparse_vectors, strict=True
        ):
            points.append(
                PointStruct(
                    id=chunk.id,
                    vector={
                        DENSE_VECTOR_NAME: NamedVector(
                            name=DENSE_VECTOR_NAME, vector=dense
                        ).vector,
                        SPARSE_VECTOR_NAME: NamedSparseVector(
                            name=SPARSE_VECTOR_NAME,
                            vector=SparseVector(
                                indices=sparse.indices, values=sparse.values
                            ),
                        ).vector,
                    },
                    payload={
                        "text": chunk.text,
                        "url": chunk.metadata.url,
                        "title": chunk.metadata.title,
                        "company": chunk.metadata.company,
                        "source_type": chunk.metadata.source_type,
                        "chunk_index": chunk.metadata.chunk_index,
                        "scraped_at": chunk.metadata.scraped_at.isoformat(),
                    },
                )
            )

        total = 0
        for i in range(0, len(points), UPSERT_BATCH_SIZE):
            batch = points[i : i + UPSERT_BATCH_SIZE]
            self._client.upsert(collection_name=COLLECTION_NAME, points=batch)
            total += len(batch)

        logger.info("Upserted %d points to Qdrant", total)
        return total

    def search(
        self,
        dense_vector: list[float],
        sparse_vector: EmbedSparseVector,
        company: str | None = None,
        limit: int = SEARCH_FUSION_LIMIT,
    ) -> list[dict[str, str]]:
        query_filter = None
        if company:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="company", match=MatchValue(value=company.strip().lower())
                    )
                ]
            )

        response = self._client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using=DENSE_VECTOR_NAME,
                    score_threshold=DENSE_SCORE_THRESHOLD,
                    limit=SEARCH_DENSE_LIMIT,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_vector.indices,
                        values=sparse_vector.values,
                    ),
                    using=SPARSE_VECTOR_NAME,
                    limit=SEARCH_SPARSE_LIMIT,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        results: list[dict[str, str]] = []
        for point in response.points:
            p = point.payload or {}
            results.append(
                {
                    "url": p.get("url", ""),
                    "title": p.get("title", ""),
                    "company": p.get("company", ""),
                    "source_type": p.get("source_type", ""),
                    "text": p.get("text", ""),
                }
            )

        logger.info("Hybrid search returned %d results", len(results))
        return results

    def delete_company(self, company: str) -> int:
        result = self._client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[FieldCondition(key="company", match=MatchValue(value=company))]
            ),
        )
        count = result.count

        if count > 0:
            self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="company", match=MatchValue(value=company))
                    ]
                ),
            )
            logger.info("Deleted %d points for company '%s'", count, company)

        return count


@lru_cache(maxsize=1)
def get_vectorstore() -> VectorStoreService:
    return VectorStoreService()
