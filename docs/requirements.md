# Requirements

## Functional Requirements

### FR-1: Company Name Input

- Accept one or more company names (English)
- Normalize input: trim, case-insensitive matching, handle common aliases (e.g., "Meta" → "Meta Platforms")
- Validate input is non-empty before triggering gather

### FR-2: Data Gathering (Online Phase)

- Scrape publicly available sources per company:
  - Company official website (landing, about, careers, blog)
  - Wikipedia article
  - Crunchbase profile
  - Recent news articles (last 12 months)
- Output: clean Markdown documents per source
- Store raw documents on filesystem for reproducibility
- Each gather run is idempotent — re-running for the same company replaces previous data

### FR-3: Text Processing Pipeline

- Convert raw HTML/structured content → clean Markdown
- Remove boilerplate (nav, footer, ads, cookie banners)
- Chunk documents into retrieval-friendly segments
- Extract and attach metadata per chunk (source URL, company, source type, timestamp)
- Generate embeddings for each chunk
- Store chunks + embeddings in vector store

### FR-4: Knowledge Base

- Single vector store instance serving all companies
- Support filtering by company name and source type
- Support similarity search over embeddings
- Persist across application restarts

### FR-5: Chat Interface (Offline Phase)

- Accept natural language questions about gathered companies
- Retrieve relevant chunks from the knowledge base
- Generate answers using local LLM — no internet access during query
- Include source citations in every answer (URL + title)
- Respond "I don't have enough information" when retrieval confidence is low
- Support multi-turn conversation with context window

### FR-6: Observability

- Emit OpenTelemetry traces for: scraping, chunking, embedding, retrieval, generation
- Track token usage per LLM call
- Unified dashboard for all telemetry

## Non-Functional Requirements

### NFR-1: Offline Operation

- Chat/query phase must work fully offline
- LLM inference: local (Ollama)
- Embeddings: local (sentence-transformers)
- Vector store: local (Qdrant)

### NFR-2: Language Scope

- English only — all processing, embeddings, and prompts assume English text
- Embedding model selected for English performance

### NFR-3: Latency

- Embedding generation: < 500ms per chunk (CPU)
- Retrieval (top-k similarity): < 200ms for 10K chunks
- End-to-end query response: bounded by LLM inference speed (model-dependent)

### NFR-4: Data Volume (POC Scope)

- Target: 5–20 companies
- ~50–200 raw documents per company
- ~500–5,000 chunks per company
- Total vector store: < 100K chunks

### NFR-5: Reproducibility

- Raw scraped documents preserved on filesystem
- Chunk IDs deterministic (hash of URL + chunk index)
- Re-running gather produces identical chunks for identical content

### NFR-6: Modularity

- Scraper, chunker, embedder, vector store, LLM — each replaceable independently
- No tight coupling between processing stages
