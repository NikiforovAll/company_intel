# Implementation Roadmap

Phased plan from zero to complete POC. Each phase produces a working system — later phases add capability, not fix breakage.

## Architecture: Single Agent, Two Capabilities

One Pydantic AI agent exposed via AG-UI protocol. No CLI. User interacts through a CopilotKit chat UI (Next.js).

The agent has two tool categories:

- **Gather tools** (online) — scrape, clean, chunk, embed, store. Triggered by user intent ("gather info about Figma").
- **Query tools** (offline) — retrieve from knowledge base, generate grounded answer. Triggered by questions ("Who are Figma's competitors?").

The LLM routes between them based on user message. Both capabilities live in a single FastAPI app, single SSE endpoint.

```
┌─────────────────────────────────────┐
│        CopilotKit Chat UI (Next.js) │
└──────────────┬──────────────────────┘
               │ SSE
┌──────────────▼──────────────────────┐
│      Pydantic AI Agent (FastAPI)    │
│                                     │
│  ┌─────────────┐  ┌──────────────┐  │
│  │ gather tool │  │ search tool  │  │
│  │ (online)    │  │ (offline)    │  │
│  └──────┬──────┘  └──────┬───────┘  │
│         │                │          │
│    Crawl4AI         Qdrant hybrid   │
│    → clean          → RRF retrieve  │
│    → chunk          → format context│
│    → embed                          │
│    → store                          │
└─────────────────────────────────────┘
```

---

## Phase 0 — Skeleton

> Goal: `dotnet run` starts everything, chat UI connects, agent responds with hardcoded answers.

| Task                        | Requirements                   | Done when                                                |
| --------------------------- | ------------------------------ | -------------------------------------------------------- |
| Python project scaffold     | uv, pyproject.toml, ruff, mypy | `uv run ruff check` and `uv run mypy src` pass           |
| FastAPI + Pydantic AI agent | Minimal agent, no tools        | `/health` returns 200                                    |
| AG-UI protocol wiring       | SSE endpoint, AG-UI events     | CopilotKit UI shows agent messages                       |
| Aspire AppHost integration  | Ollama + Qdrant + Python agent | `dotnet run` starts all services, dashboard shows health |

**Requires**: FR-5 (chat interface), NFR-1 (offline operation)
**Validates**: Aspire polyglot orchestration, AG-UI protocol, end-to-end connectivity

---

## Phase 1 — Gather Pipeline

> Goal: user says "gather Figma" in chat → agent scrapes, chunks, embeds, stores. Reports progress via chat messages.

| Task                                   | Requirements         | Done when                                                  |
| -------------------------------------- | -------------------- | ---------------------------------------------------------- |
| `gather` agent tool                    | FR-1, FR-2           | Agent recognizes gather intent, invokes tool with company name |
| Crawl4AI scraper — website + Wikipedia | FR-2                 | Raw Markdown files saved to `data/{company}/raw/`          |
| Text cleaning                          | Constraints §2       | Boilerplate removed, min/max length enforced, English only |
| Semantic chunking                      | FR-3, Constraints §3 | Chunks 256-512 tokens, metadata attached                   |
| Embedding generation                   | Constraints §4       | Dense vectors (384-dim, arctic-embed-s) per chunk          |
| Sparse vector generation               | Constraints §5       | BM25 tokenized vectors per chunk                           |
| Qdrant ingestion                       | FR-4                 | Chunks searchable with metadata filtering                  |
| Idempotent re-gather                   | FR-2, NFR-5          | Re-running same company replaces previous data             |
| Progress feedback via chat             | —                    | Agent streams status ("scraping website...", "chunking 42 documents...") |

**Requires**: FR-1 (input), FR-2 (gathering), FR-3 (processing), FR-4 (knowledge base), NFR-5 (reproducibility)
**Validates**: Full data pipeline, Crawl4AI → Markdown → chunks → Qdrant, tool invocation via chat

---

## Phase 2 — RAG Query

> Goal: ask questions about gathered companies, get grounded answers with citations.

| Task                                  | Requirements         | Done when                                               |
| ------------------------------------- | -------------------- | ------------------------------------------------------- |
| `search` agent tool — hybrid retrieval | FR-5, Constraints §6 | Top-k chunks via RRF (BM25 + dense), company filter     |
| System prompt — grounding + citations | FR-5                 | Answers reference source URLs, no hallucination         |
| Confidence threshold                  | FR-5                 | "I don't have enough information" when cosine < 0.3     |
| Company filter inference              | Constraints §6       | LLM infers company from conversation context            |
| Multi-turn conversation               | FR-5                 | Sliding window (≤ 4K tokens history), context preserved |
| Token budget enforcement              | Constraints §7       | system + context + history + headroom ≤ 32K             |

**Requires**: FR-5 (chat), NFR-1 (offline)
**Validates**: RAG quality, grounding, citation accuracy

---

## Phase 3 — Observability

> Goal: full pipeline visibility in Aspire Dashboard.

| Task                                        | Requirements | Done when                                   |
| ------------------------------------------- | ------------ | ------------------------------------------- |
| OTel instrumentation — scraping             | FR-6         | Spans for each scrape request with status   |
| OTel instrumentation — chunking + embedding | FR-6         | Spans with chunk count, duration            |
| OTel instrumentation — retrieval            | FR-6         | Spans with query, top-k scores, filter used |
| OTel GenAI conventions — LLM calls          | FR-6         | Token usage, model, prompt/completion spans |
| Aspire Dashboard integration                | FR-6         | Traces visible end-to-end in dashboard      |

**Requires**: FR-6 (observability)
**Validates**: OTel GenAI semantic conventions, Logfire + Aspire integration

---

## Phase 4 — Additional Sources

> Goal: broader data coverage beyond website + Wikipedia.

| Task                            | Requirements | Done when                                            |
| ------------------------------- | ------------ | ---------------------------------------------------- |
| News scraper                    | FR-2         | Recent articles (last 12 months) scraped and chunked |
| Crunchbase scraper              | FR-2         | Company profile data extracted                       |
| Source-specific cleaning rules  | FR-3         | Each source type produces clean Markdown             |
| Error handling — partial gather | —            | Failure in one source doesn't block others           |

**Requires**: FR-2 (all source types)
**Validates**: Scraping resilience, source diversity

---

## Phase 5 — Validate & Tune

> Goal: evidence that the system works, not just belief.

| Task                      | Requirements | Done when                                       |
| ------------------------- | ------------ | ----------------------------------------------- |
| Golden test dataset       | —            | 5+ companies, 10+ Q&A pairs each                |
| Retrieval metrics         | —            | recall@10, MRR measured per query               |
| Answer quality evaluation | —            | Grounding accuracy, citation correctness scored |
| Parameter tuning          | —            | Threshold, top-k, chunk size justified by data  |
| End-to-end demo script    | —            | Scripted gather + query for 3 companies         |

**Validates**: All parameter choices in [constraints.md](constraints.md) are backed by measurement

---

## Dependency Graph

```
Phase 0 (Skeleton)
  └── Phase 1 (Gather)
        ├── Phase 2 (RAG Query)
        │     └── Phase 5 (Validate)
        └── Phase 4 (Sources)
  └── Phase 3 (Observability) — can start after Phase 0
```

Phase 3 is independent of Phases 1-2 — OTel setup can happen in parallel.

## Open Items

Tracked in [_draft/OPEN_QUESTIONS.md](_draft/OPEN_QUESTIONS.md):

- System prompt design (blocks Phase 2)
- Testing strategy details (blocks Phase 5)
