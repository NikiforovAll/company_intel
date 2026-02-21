# Open Questions

## ~~2. Data Model / Schema~~ — RESOLVED

Defined in `docs/constraints.md` and `docs/_draft/DATA_STRATEGY.md`. Models: `RawDocument`, `Chunk`, `ChunkMetadata`. Dedup via `sha256(url + chunk_index)` chunk IDs.

## 4. System Prompt Design

The RAG agent needs a well-crafted prompt to:

- Stay grounded in the knowledge base only
- Cite sources in every answer
- Say "I don't know" when retrieval confidence is low
- Handle follow-up questions within a conversation

## 5. Testing / Validation Strategy

How do we know retrieval quality is good enough?

- Define sample questions per company as a test suite?
- Measure retrieval precision/recall?
- Use Pydantic AI evals?

## 6. Implementation Roadmap

No phased plan defined. Suggested iteration order:

- **v0**: Single-source scrape (website only) + basic chat
- **v1**: Multi-source + semantic chunking + citations
- **v2**: Aspire orchestration + OTel observability
- **v3**: polish
