# Tradeoff: Retrieval Strategy

## Decision: Hybrid search (BM25 + vector) via Qdrant RRF + optional metadata filtering + optional reranking

## Why RRF for Company Intelligence

Company intel queries fall into two distinct categories that **neither search method handles alone**:

### Semantic queries (dense vector wins)

- "What is Spotify's business model?" → needs semantic understanding of "business model" across chunks about revenue, subscriptions, pricing
- "How does Airbnb make money?" → "make money" must match chunks about "revenue streams", "commission fees", "service charges"
- "Who are Figma's competitors?" → must connect "competitors" with chunks mentioning "Adobe", "Sketch", "Canva" in competitive context

Dense embeddings encode meaning — "make money" is close to "revenue" in vector space. BM25 would miss this entirely because the exact words don't match.

### Entity queries (BM25 wins)

- "When was Spotify's Series B?" → "Series B" is a specific term, not a semantic concept. Dense search may return chunks about Series A or Series C because they're semantically similar
- "Who is Brian Chesky?" → a proper name has no semantic meaning to an embedding model. BM25 matches the exact string
- "What was Figma's $20B acquisition price?" → "$20B" is a token, not a meaning. Dense search treats all dollar amounts as roughly equivalent

BM25 scores by exact term frequency — "Series B" matches "Series B", not "Series A". Dense search can't distinguish these reliably.

### RRF fuses both without score calibration

```
RRF_score(doc) = 1/(k + rank_dense) + 1/(k + rank_bm25)     k=60
```

A document ranked high by **both** methods gets the highest fused score. A document ranked high by only one still appears, just lower. No score normalization needed — only rank positions matter, so incompatible score scales (cosine 0-1 vs BM25 unbounded) aren't a problem.


## Retrieval Strategies Compared

| Strategy | Precision | Recall | Latency | Complexity |
|----------|:---------:|:------:|:-------:|:----------:|
| Vector similarity only | Medium | Medium | Low | Low |
| Vector + metadata filter | Medium-High | Medium | Low | Low |
| **Hybrid (BM25 + vector) via RRF** | High | High | Medium | Medium |
| Hybrid + reranker | Highest | High | Higher | High |
| Multi-hop retrieval | Variable | Highest | High | Very High |

## Query Flow

```
User query → embed (dense) + tokenize (BM25 sparse)
    → optional company filter (when LLM infers from context)
    → Qdrant prefetch: top-20 dense + top-20 sparse
    → RRF fusion → top-10
    → LLM context
```

**Pros:**
- Catches both semantic and entity queries
- RRF is parameter-light (only k=60, no weight tuning needed)
- Server-side fusion in Qdrant — single round-trip, no client-side merging
- Sub-200ms for < 100K chunks

**Cons:**
- Requires dual indexing (dense + sparse vectors per chunk) — doubles index size
- BM25 tokenization adds ingestion overhead
- Over-retrieval (top-20 from each branch) means more candidates to process

## Reranking (deferred)

After initial retrieval, a cross-encoder scores each (query, chunk) pair. Highest-ROI improvement to precision — but adds latency and another model to host.

| Reranker | Size | Speed | Quality |
|----------|:----:|:-----:|:-------:|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | 80 MB | Fast | Good |
| `BAAI/bge-reranker-base` | 1.1 GB | Medium | Better |

**When to add:** If evaluation shows top-10 RRF results contain irrelevant chunks that hurt answer quality. The flow becomes: RRF top-20 → reranker → top-5 → LLM.

## Top-K Selection

With 32K context window (Qwen3), we have more budget than before:

| k | Context Tokens (~) | Coverage |
|:-:|:-----------------:|:--------:|
| 5 | ~1,500 | Medium |
| **8–10** | ~2,500–3,000 | Good — chosen |
| 15 | ~4,500 | High |
| 20 | ~6,000 | Overkill, "lost in the middle" risk |

**Decision:** RRF over-retrieves top-20 per branch, fuses to top-10 for LLM context. Stays within 4,000-token retrieval budget.

## Similarity Threshold

**Minimum cosine similarity: 0.3**

- Below 0.3 → likely irrelevant noise
- Above 0.7 → high confidence
- No chunks pass threshold → "I don't have enough information about that."

Note: threshold applies to dense scores only. BM25 scores are rank-based in RRF — no threshold needed.

## Query Preprocessing

1. Company name prepended by LLM when inferred from conversation (optional)
2. No query expansion in POC
3. Conversation context: last user message + assistant summary, not full history
