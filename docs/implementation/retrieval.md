# Hybrid Retrieval Pipeline

## Query Flow

```
user query
    → embed_query()              # dense (Ollama) + sparse (fastembed BM25)
    → vectorstore.search()       # Qdrant hybrid search with RRF fusion
    → _apply_context_budget()    # trim to 3,000 tiktoken tokens
    → LLM context
```

## Hybrid Search Design

Two-branch retrieval fused via Reciprocal Rank Fusion (RRF):

| Branch | Vector | Model | Limit | Notes |
|--------|--------|-------|-------|-------|
| Dense | `dense` (384-dim, cosine) | snowflake-arctic-embed:33m via Ollama | 10 | `score_threshold=0.45` filters low-quality matches |
| Sparse | `sparse` (BM25) | Qdrant/bm25 via fastembed | 10 | Exact keyword matching |

RRF score: `sum(1 / (k + rank_i))` per candidate across both ranked lists (k=60 default). This balances semantic similarity (dense) with keyword precision (sparse).

## Qdrant `query_points` API

```python
response = client.query_points(
    collection_name=COLLECTION_NAME,
    prefetch=[
        Prefetch(query=dense_vector, using="dense",
                 score_threshold=0.45, limit=10),
        Prefetch(query=SparseVector(indices=..., values=...),
                 using="sparse", limit=10),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    query_filter=company_filter,  # optional keyword filter on "company" field
    limit=5,
)
```

- `prefetch` runs both branches independently
- `FusionQuery(fusion=Fusion.RRF)` merges the two ranked lists
- `query_filter` applies pre-filtering (before vector search) on indexed payload fields
- Company filter normalizes to lowercase: `company.strip().lower()`

## Context Budget Enforcement

After retrieval, `_apply_context_budget()` greedily packs results until the token budget (3,000 tokens, tiktoken `cl100k_base`) is exhausted. This prevents overloading the LLM's context window with too many chunks.

The budget is conservative — Qwen3 8B has 32K context, but we reserve most of it for conversation history, instructions, and generation.

## Configuration

Constants in `agent/vectorstore/config.py`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `SEARCH_DENSE_LIMIT` | 10 | Dense branch candidate count |
| `SEARCH_SPARSE_LIMIT` | 10 | Sparse branch candidate count |
| `SEARCH_FUSION_LIMIT` | 5 | Final results after RRF fusion |
| `DENSE_SCORE_THRESHOLD` | 0.45 | Minimum cosine similarity for dense branch |
| `CONTEXT_BUDGET_TOKENS` | 3000 | Max tokens sent to LLM as context |

## Wiring in the Chat Agent

`agent/app.py` → `search_knowledge_base` tool:

1. `get_embedder().embed_query(query)` — produces `(dense_vec, sparse_vec)` for the query
2. `get_vectorstore().search(dense_vec, sparse_vec, company=company)` — hybrid search
3. `_apply_context_budget(results)` — trim to token budget
4. Return results to the agent (list of dicts with `url`, `title`, `company`, `source_type`, `text`)

Both `get_embedder()` and `get_vectorstore()` are `@lru_cache(maxsize=1)` singletons — no repeated initialization cost.
