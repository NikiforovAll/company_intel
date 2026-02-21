# vNext — Known Improvements

Improvements we recognize but deliberately defer. Each entry explains what we'd do, why it's better, and why we don't do it yet.

## 1. Separate Gather Worker Process

**Current**: Scraping, chunking, and embedding run inside the agent process. A long gather blocks the agent's event loop.

**Improvement**: Extract gather into a background worker (e.g., Celery, ARQ, or a separate FastAPI service). Agent enqueues a gather job and polls for completion. Aspire orchestrates both services.

**Why not yet**: Single-process is simpler to debug and deploy. POC gathers ~5-20 companies — blocking is acceptable. Separation adds message queue infrastructure (Redis/RabbitMQ) with no POC benefit.

## 2. Incremental Scraping (Content Hash + TTL)

**Current**: Each gather wipes all data for the company and re-scrapes everything from scratch (idempotent fresh gather).

**Improvement**: Store content hash per page. On re-gather, skip unchanged pages, only re-scrape stale sources (TTL-based). Reduces scrape time and avoids unnecessary re-embedding.

**Why not yet**: With 5-20 companies and 20 pages per source, full re-scrape takes minutes. The cost of re-embedding unchanged content is negligible at POC scale.

## 3. Cross-Encoder Reranker

**Current**: Hybrid retrieval (BM25 + dense via RRF) returns top-k chunks directly to the LLM.

**Improvement**: Add a cross-encoder reranking stage after initial retrieval. Retrieve top-20 candidates, rerank with a cross-encoder (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`), return top-5. Significantly improves precision for ambiguous queries.

**Why not yet**: Adds ~200-500ms latency per query on CPU. Current hybrid retrieval quality is untested — measure first (Phase 5), add reranker only if retrieval precision is insufficient.

## 4. Evaluation Pipeline

**Current**: No automated quality measurement. Parameter choices (0.3 cosine threshold, top-10, 512 token chunks) are based on literature, not validated on our data.

**Improvement**: Build an evaluation harness — golden Q&A dataset per company, measure recall@k, MRR, answer grounding accuracy, citation correctness. Run as CI step on parameter changes.

**Why not yet**: Requires a curated test dataset that doesn't exist yet. Building the system first, then validating (Phase 5 in roadmap). Premature optimization of parameters without a working pipeline is wasteful.

## 5. Structured Data Extraction

**Current**: All scraped content is treated as unstructured text — chunked and embedded uniformly.

**Improvement**: Extract structured fields (founded date, CEO, funding rounds, revenue, employee count) into a separate store or Qdrant payload fields. Enable direct field lookups ("When was Figma founded?" → exact answer without retrieval) and comparative queries ("Compare funding of Figma vs Canva").

**Why not yet**: Requires source-specific extraction logic (Crunchbase schema differs from Wikipedia infoboxes). The unstructured RAG approach handles these queries acceptably for a POC. Structured extraction is a significant scope increase with diminishing returns until source coverage (Phase 4) is complete.

## 6. Conversation Length Management (Context Window)

**Current**: Chat agent sends the full conversation history to the LLM on every turn. With Qwen3 8B's 32K context window, long conversations will eventually exceed the limit — causing truncation, degraded answers, or outright failures.

**Improvement**: Implement a conversation management strategy. Options (not mutually exclusive):

- **Sliding window**: Keep only the last N turns, drop older messages.
- **Conversation summarization**: Periodically summarize older turns into a compact system message, preserving key facts while freeing token budget.
- **Token-aware truncation**: Count tokens before each request; when approaching the limit, trigger summarization or trim oldest turns.
- **Explicit "new topic" reset**: Let the user clear history via UI when switching topics.

**Why not yet**: POC conversations are short (5-15 turns). The 32K window is sufficient for demo scenarios. Summarization adds latency and complexity (extra LLM call per summarization cycle). Worth addressing once real usage patterns reveal actual conversation lengths.
