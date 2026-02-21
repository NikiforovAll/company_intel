# Tradeoff: Vector Store

## Decision: Qdrant

Previously: ChromaDB. Changed because Qdrant provides pre-search filtering (filters during HNSW traversal), mature hybrid search with RRF fusion, and first-party Aspire integration (`Aspire.Hosting.Qdrant`).

## Alternatives Considered

| Store | Type | Hybrid Search | Filtering | Aspire Integration | Setup Complexity |
|-------|------|:------------:|:---------:|:-----------------:|:----------------:|
| **Qdrant** | Client-Server | Yes (prefetch + RRF/DBSF) | Pre-search (filterable HNSW) | First-party | Docker / local mode |
| ChromaDB | Embedded/Client-Server | Yes (new Search API + Rrf) | Post-search (filter after) | None (AddContainer hack) | Minimal |
| Milvus | Distributed | Yes | Rich filters | None | Complex |
| FAISS | In-memory library | No | No native | None | Code-only |
| pgvector | PostgreSQL extension | Via pg_search | Full SQL | First-party | PostgreSQL needed |

## Why Qdrant

**Pros:**
- **Pre-search filtering** — filters applied during HNSW graph traversal, not after. Always returns the requested k results when filtering by company
- **Mature hybrid search** — `prefetch` branches (dense + sparse) fused via `Fusion.RRF`. Battle-tested API
- **First-party Aspire integration** — `AddQdrant("qdrant")` with health checks, API key, dashboard access. No `AddContainer` workaround
- **Local mode without Docker** — `QdrantClient(path="./local")` for dev, same as ChromaDB's simplicity
- **Multi-vector per document** — separate vectors for title/body if needed later
- **Built-in dashboard** at `:6333/dashboard`

**Cons:**
- Slightly more setup than ChromaDB for first-time users
- Sparse vector setup requires explicit `SparseVectorParams` configuration
- Larger Docker image than ChromaDB

## Why Not ChromaDB (previous choice)

ChromaDB now supports hybrid search (BM25 + RRF) via a new `Search()` API. However:
- **Post-search filtering** — filters applied after HNSW search. When filtering by company, may return fewer results than requested
- **No Aspire package** — required manual `AddContainer` with hardcoded ports
- **Newer hybrid API** — less battle-tested than Qdrant's

ChromaDB remains excellent for quick prototypes where filtering and hybrid search aren't critical.

## Hybrid Search with RRF

Qdrant supports Reciprocal Rank Fusion natively:

```python
results = client.query_points(
    collection_name="company_intel",
    prefetch=[
        models.Prefetch(query=sparse_vector, using="sparse", limit=20),
        models.Prefetch(query=dense_vector, using="dense", limit=20),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=10,
)
```

This retrieves top-20 from both BM25 (sparse) and semantic (dense) search, then fuses via RRF — documents appearing in both lists get boosted. Catches both exact entity matches and semantic similarity.

## Collection Design

Single collection with optional metadata filtering:

| Approach | Filtering | Use Case |
|----------|:---------:|:--------:|
| `filter={"company": "Spotify"}` | Single company | "What is Spotify's revenue?" |
| No filter | Cross-company | "Compare Spotify and Airbnb" |

Company filter is optional — inferred by the LLM from conversation context. Qdrant's pre-search filtering ensures correct results when applied.

## Key Decision Factors

1. **Pre-search filtering** — correct results when company filter is applied
2. **RRF hybrid search** — entity-heavy queries need BM25 + vector fusion
3. **Aspire first-party** — `Aspire.Hosting.Qdrant` vs manual container config
4. **Easy migration** — Python client API is similar complexity to ChromaDB
