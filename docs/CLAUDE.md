# Docs

## Core

| Doc                                  | What it covers                                                  |
| ------------------------------------ | --------------------------------------------------------------- |
| [SPEC.md](SPEC.md)                   | Original task spec from OBRIO                                   |
| [requirements.md](requirements.md)   | Functional (FR-1→6) and non-functional (NFR-1→6) requirements   |
| [constraints.md](constraints.md)     | Hard bounds for every pipeline stage (scraping → generation)    |
| [data-strategy.md](data-strategy.md) | Data model, storage layout, chunking, embedding, retrieval flow |
| [drivers.md](drivers.md)             | Technology choices with rationale                               |
| [roadmap.md](roadmap.md)             | Phased implementation plan (Phase 0→5)                         |
| [vnext.md](vnext.md)                 | Known improvements, deliberately deferred                      |

## Tradeoff Analysis

Each doc compares alternatives and documents the decision.

| Doc                                                                | Decision                                                   |
| ------------------------------------------------------------------ | ---------------------------------------------------------- |
| [tradeoffs/01-scraping.md](tradeoffs/01-scraping.md)               | Crawl4AI over Firecrawl, BeautifulSoup, Scrapy             |
| [tradeoffs/02-text-processing.md](tradeoffs/02-text-processing.md) | Semantic chunking on Markdown (256-512 tokens)             |
| [tradeoffs/03-embeddings.md](tradeoffs/03-embeddings.md)           | snowflake-arctic-embed-s (384-dim) over MiniLM             |
| [tradeoffs/04-vector-store.md](tradeoffs/04-vector-store.md)       | Qdrant over ChromaDB (pre-search filtering, hybrid search) |
| [tradeoffs/05-embedding-runtime.md](tradeoffs/05-embedding-runtime.md) | Ollama dense + fastembed BM25, tiktoken for counting   |
| [tradeoffs/05-retrieval.md](tradeoffs/05-retrieval.md)             | Hybrid RRF (BM25 + dense) over vector-only                 |
| [tradeoffs/06-llm-inference.md](tradeoffs/06-llm-inference.md)     | Qwen3 8B (32K context) over Llama3 (8K)                    |
| [tradeoffs/07-ui.md](tradeoffs/07-ui.md)                         | CopilotKit + Next.js over AG-UI Dojo (minimal standalone UI)   |

## Implementation

| Doc                                                              | What it covers                                              |
| ---------------------------------------------------------------- | ----------------------------------------------------------- |
| [implementation/scraper.md](implementation/scraper.md)           | Scraper pipeline: Crawl4AI, URL resolution, text cleaning   |
| [implementation/chunking-embedding.md](implementation/chunking-embedding.md) | Chunking, embedding & Qdrant ingestion pipeline |

## Misc

| Doc                                                                                  | What it covers                                 |
| ------------------------------------------------------------------------------------ | ---------------------------------------------- |
| [misc/research.md](misc/research.md)                                                 | OSINT tools, RAG frameworks, tech stack survey |
| [misc/critique.md](misc/critique.md)                                                 | Devil's advocate review — open risks           |
| [misc/chromadb-vs-qdrant-hybrid-search.md](misc/chromadb-vs-qdrant-hybrid-search.md) | Deep comparison with code examples             |

## Drafts

Working documents, not finalized. `_draft`
