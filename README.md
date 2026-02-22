# Company Intelligence

RAG-based company research assistant. Two-phase system: (1) ingest company data from public sources, (2) ask questions offline with grounded, cited answers.

[![Deploy presentation to Pages](https://github.com/NikiforovAll/company_intel/actions/workflows/marp-pages.yml/badge.svg)](https://nikiforovall.blog/company_intel/rag-pydantic-ai-example)

## How it works

```
Phase 1: INGEST (online)              Phase 2: QUERY (offline)
───────────────────────────            ────────────────────────
"Add data about PayPal"                "Who is PayPal's CEO?"
  → Crawl4AI scrapes sources            → Hybrid retrieval (Qdrant)
  → Clean HTML → Markdown               → RRF fusion (dense + BM25)
  → Semantic chunking                   → LLM generates grounded answer
  → Embed (dense + BM25 sparse)         → Citations from stored knowledge
  → Upsert to Qdrant
```

## Screenshots

| Backoffice — data ingestion | Chat — Q&A with citations |
|:---:|:---:|
| ![backoffice](assets/backoffice_01.png) | ![chat](assets/chat-02.png) |

| Distributed traces | Scraper metrics |
|:---:|:---:|
| ![traces](assets/backoffice_02.png) | ![metrics](assets/backoffice_03.png) |

## Tech stack

| Layer | Choice |
|-------|--------|
| LLM | Qwen3 8B via Ollama (32K context, local-only) |
| Embeddings | snowflake-arctic-embed-s (384-dim) |
| Vector store | Qdrant (hybrid search, RRF fusion) |
| Agent framework | Pydantic AI + AG-UI protocol |
| Frontend | CopilotKit + Next.js 15 |
| Orchestration | .NET Aspire |
| Scraping | Crawl4AI |
| Observability | OpenTelemetry via Logfire → Aspire dashboard |

## Quick start

```bash
# Prerequisites: .NET 10 SDK, Node.js 20+, Python 3.12+, uv

# One-time: setup Crawl4AI browser
cd src/agent && uv run crawl4ai-setup

# Start everything
dotnet run --project src/AppHost
```

This starts Ollama (+ model pulls), Qdrant, Python agent, and Next.js UI via .NET Aspire. Open the Aspire dashboard link from terminal output.

## Project structure

```
src/AppHost/   → .NET Aspire orchestrator
src/agent/     → Python FastAPI backend (Pydantic AI agents)
src/ui/        → Next.js 15 frontend (CopilotKit + AG-UI)
docs/          → Design docs, tradeoffs, implementation notes
slides/        → Marp presentation (GitHub Pages)
```

## Presentation

[View slides](https://nikiforovall.blog/company_intel/rag-pydantic-ai-example)
