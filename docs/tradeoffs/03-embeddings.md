# Tradeoff: Embedding Model

## Decision: `snowflake-arctic-embed-s`

Previously: `all-MiniLM-L6-v2`. Changed because arctic-embed-s is a drop-in replacement (same 384 dims, same 512 tokens) with ~10 point better retrieval on MTEB.

## Alternatives Considered

| Model                         | Dims  | Max Tokens |  Size  | MTEB Retrieval (nDCG@10) | Speed (CPU) |
| ----------------------------- | :---: | :--------: | :----: | :----------------------: | :---------: |
| all-MiniLM-L6-v2              |  384  |    256     | 80 MB  |           ~41            |   Fastest   |
| bge-small-en-v1.5             |  384  |    512     | 130 MB |          51.68           |    Fast     |
| **snowflake-arctic-embed-s**  |  384  |    512     | 130 MB |        **51.98**         |    Fast     |
| nomic-embed-text-v1.5         |  768  |    8192    | 262 MB |          ~52.8           |   Medium    |
| snowflake-arctic-embed-m-v2.0 |  768  |    8192    | 450 MB |           55.4           |   Medium    |
| jina-embeddings-v5-text-nano  |  768  |    8192    | 480 MB |           58.8           |   Medium    |
| OpenAI text-embedding-3-small | 1536  |    8191    |  API   |            —             | N/A (cloud) |

## Why snowflake-arctic-embed-s

**Pros:**
- Best retrieval score among 384-dim models (51.98 nDCG@10)
- Same 384 dimensions as MiniLM — no vector store migration needed
- 512 token context — matches our chunk size constraint exactly
- 130 MB — small enough for any machine, fast CPU inference
- Retrieval-optimized training (not general STS) — exactly what RAG needs
- Apache 2.0 license

**Cons:**
- 512 token limit — chunks must stay within this bound
- 384 dims captures less nuance than 768-dim models
- Retrieval-focused — less versatile for other NLP tasks (irrelevant for our use case)
- Smaller community than sentence-transformers models

## Why Not the "Better" Models

### nomic-embed-text-v1.5 / snowflake-arctic-embed-m-v2.0 / jina-v5-nano

All are measurably better on retrieval (52.8–58.8 vs 51.98). But:

1. **768 dimensions doubles vector storage and search cost** — unnecessary at POC scale
2. **8K context is wasted** — our chunks are 512 tokens, long context adds no value
3. **260–480MB vs 130MB** — more RAM, slower loading
4. **Changing from 384→768 dims requires vector store reconfiguration** — churn for marginal gain
5. **We haven't validated retrieval on real data yet** — optimizing embeddings before measuring is premature

### all-MiniLM-L6-v2 (previous choice)

- **Only 256 token max context** — we documented 512 as our chunk target, so MiniLM would silently truncate chunks. This alone disqualifies it.
- ~10 points worse on retrieval benchmarks
- 2021-era model, pre-dates retrieval-specific training advances

### bge-small-en-v1.5

- Very close competitor (51.68 vs 51.98). Either would work.
- Arctic-embed-s edges it on retrieval specifically. bge-small requires query prefix instructions which adds implementation complexity.

## Key Decision Factors

1. **Drop-in replacement** — same dims (384), same token limit (512), no infra changes
2. **Retrieval-optimized** — trained specifically for the task we need, not general STS
3. **Must run locally on CPU** — 130MB, fast inference
4. **English only** — no need for multilingual overhead

## Dimension Size Impact

| Dims  | Vector Size | 100K Chunks Storage | Search Speed |
| :---: | :---------: | :-----------------: | :----------: |
|  384  |   1.5 KB    |       ~150 MB       |   Fastest    |
|  768  |    3 KB     |       ~300 MB       |     Fast     |
| 1536  |    6 KB     |       ~600 MB       |    Slower    |

384 remains the right choice for POC — minimal storage, fast search, good-enough quality.

## When to Upgrade

Upgrade to `snowflake-arctic-embed-m-v2.0` (768d, 55.4 retrieval, 8K context) if:
- Retrieval quality is measurably poor on evaluation set
- Scale grows beyond POC (> 100K chunks)
- Chunk strategy changes to larger chunks (> 512 tokens)

Switching cost: re-embed all chunks (batch job), update ChromaDB collection config for 768 dims.
