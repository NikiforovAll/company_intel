---
marp: true
title: Company Intelligence
author: Oleksii Nikiforov
size: 16:9
theme: copilot
pagination: true
footer: ""
---

<!-- _class: lead -->

![bg fit](./img/bg-title.png)

# **Company Intelligence**
## RAG-based company research assistant

---

<!-- _class: hero -->

![bg left:35% brightness:1.00](./img/oleksii.png)

## Oleksii Nikiforov

- Lead Software Engineer at EPAM Systems
- AI Engineering Coach
- +10 years in software development
- Open Source and Blogging

<br/>

> <i class="fa-brands fa-github"></i> [nikiforovall](https://github.com/nikiforovall)
<i class="fa-brands fa-linkedin"></i> [Oleksii Nikiforov](https://www.linkedin.com/in/nikiforov-oleksii/)
<i class="fa fa-window-maximize"></i> [nikiforovall.blog](https://nikiforovall.blog/)

---

![bg fit](./img/bg-slide-alt3.png)

# Problem Statement

- Company research is **manual, repetitive, scattered**
- Data lives across websites, Wikipedia, news, Crunchbase
- Goal: **ask questions → get grounded answers**

---

![bg fit](./img/bg-slide-alt2.png)

# Solution Overview

## Two-phase architecture

```
Phase 1: INGEST (online)          Phase 2: QUERY (offline)
─────────────────────────         ────────────────────────
User: "ingest Figma"              User: "Who are competitors?"
  → Scrape websites               → Hybrid retrieval (Qdrant)
  → Clean → Chunk → Embed         → RRF fusion (dense + BM25)
  → Store in Qdrant               → LLM generates grounded answer
```

<br/>

<div class="key">

**Key:** No internet access during query phase — answers from stored knowledge only

</div>

---

# Chat — Chat Window

![center](./img/chat-01.png)

---
# Chat — Q&A with Citations

![center](./img/chat-02.png)

---

# Chat — Detailed Research

![center](./img/chat-03.png)

---

# Backoffice — Data Ingestion

![center](./img/backoffice_01.png)

---

![bg fit](./img/bg-slide-alt2.png)

# Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Qwen3 8B via Ollama | 32K context, local-only |
| Embeddings | snowflake-arctic-embed-s | 384-dim, fast on CPU |
| Vector Store | Qdrant | Hybrid search, pre-filtering |
| Agent | Pydantic AI + AG-UI | SSE streaming to UI |
| Frontend | CopilotKit + Next.js 15 | React 19, chat UX |
| Orchestration | .NET Aspire | Service discovery, OTel |
| Scraping | Crawl4AI | Async, headless browser |

---

![bg fit](./img/bg-section.png)

# Phase 1: **Data Ingestion**

## Scrape → Clean → Chunk → Embed → Store

---

![bg fit](./img/bg-slide-alt3.png)

# Ingestion Pipeline

```
Ingest triggered
  → Normalize company name
  → Wipe existing data (idempotent)
  → Scrape all sources (Crawl4AI)
  → Clean HTML → Markdown
  → Semantic chunking (256–512 tokens)
  → Dense embedding (arctic-embed-s, 384-dim)
  → Sparse vectors (BM25 tokenization)
  → Upsert to Qdrant
  → Knowledge base ready
```

---

![bg fit](./img/bg-slide-alt1.png)

# Scraping

- **Crawl4AI** — async, headless browser, Markdown output
- Sources: company website, Wikipedia, news articles
- Bounds: max 20 pages/source, 30s timeout, 1 req/s rate limit
- Respects robots.txt, English-only filter

---

![bg fit](./img/bg-slide-alt2.png)

# Chunking & Embedding

- **Semantic chunking** — split by headings, then paragraphs, then sentences
- Target: 256–512 tokens, 50-token overlap
- **Dense vectors**: `snowflake-arctic-embed-s` (384-dim, L2-normalized)
- **Sparse vectors**: BM25 tokenization via fastembed
- Deterministic chunk IDs: `sha256(url + chunk_index)`

---

![bg fit](./img/bg-section.png)

# Phase 2: **RAG Query**

## Retrieve → Augment → Ground → Cite

---

![bg fit](./img/bg-slide-alt2.png)

# Hybrid Retrieval

```
User query
  → Dense embed + BM25 tokenize
  → Company filter (LLM-inferred from context)
  → Qdrant prefetch: top-20 dense + top-20 sparse
  → RRF fusion (k=60) → top-10
  → Similarity threshold (cosine ≥ 0.45)
  → ≤ 4,000 tokens context → LLM
```

<br/>

<div class="tip">

**RRF** (Reciprocal Rank Fusion) combines dense and sparse rankings

</div>

---

![bg fit](./img/bg-slide-alt1.png)

# Chat Agent

- **Grounded answers** — exclusively from retrieved context
- **Citations** — every answer references source URL + title
- **Confidence** — "I don't have enough information" when cosine < 0.45
- **Multi-turn** — full history within 32K context window
- **Context budget** — ≤ 3,000 tokens retrieved context per query

---

![bg fit](./img/bg-section.png)

# Phase 3: **Orchestration & Observability**

## .NET Aspire + OpenTelemetry

---

![bg fit](./img/bg-slide-alt2.png)

# .NET Aspire

- **Polyglot orchestrator** — Python (FastAPI) + Node.js (Next.js) + containers (Ollama, Qdrant)
- Single `dotnet run` starts everything
- Service discovery — connection strings injected automatically
- Health monitoring via Aspire dashboard

---

![bg fit](./img/bg-slide-alt2.png)

# OpenTelemetry

- Instrumented via **Logfire** (HTTP/protobuf to Aspire dashboard)
- Traces for: scraping, chunking, embedding, retrieval, generation
- GenAI semantic conventions — token usage per LLM call
- End-to-end distributed tracing across all services

---

# Distributed Traces

![center](./img/backoffice_02.png)

---

# Scraper Metrics

![center](./img/backoffice_03.png)

---

![bg fit](./img/bg-section.png)

# Phase 4: **RAG Evaluation**

## Measure retrieval quality before it reaches the LLM

---

![bg fit](./img/bg-slide-alt2.png)

# Evaluation Approach

```
Golden dataset (curated Q&A pairs with expected facts)
  → Ingest raw data into vector store
  → Run each query through retrieval pipeline
  → Check: did retrieved chunks contain expected facts?
  → Compute Hit Rate & Context Recall
  → Assert thresholds in CI
```

<br/>

<div class="key">

**Key:** Evaluation runs as an integration test — Aspire starts all services, eval runs end-to-end

</div>

---

![bg fit](./img/bg-slide-alt2.png)

# Why Aspire for Eval?

- **Clean environment** — fresh Qdrant container per test run, no stale data
- **Isolation** — all services (Ollama, Qdrant, agent) spun up and torn down automatically
- **No port conflicts** — Aspire assigns random ports, test discovers them via service name
- **One command** — `dotnet test` boots the entire stack, runs eval, asserts thresholds
- **Same pipeline** — eval exercises the real ingestion + retrieval

<div class="tip">

**Benefit:** Confidence that eval results reflect production behavior — not a simulated environment

</div>

---

![bg fit](./img/bg-slide-alt2.png)

# Metrics

| Metric | What it measures |
|--------|-----------------|
| **Hit Rate** | % of queries where *at least one* expected fact is retrieved |
| **Context Recall** | Average % of expected facts found per query |

<br/>

- **Substring matching** — each expected fact checked against retrieved chunks
- No LLM involvement — deterministic, fast 
- We could use LLM-as-judge for semantic matching, but substring is sufficient here
- Golden dataset: 18 queries, 2–4 reference facts each

---

![bg fit](./img/bg-slide-alt1.png)

# Best Practices for RAG Evaluation

- **Golden datasets** — curated Q&A pairs with ground-truth contexts
- **Separate retrieval from generation** — measure each independently
- **LLM-as-judge** — use strong LLM to score answer faithfulness & relevance
- **Multiple metrics** — precision, recall, MRR, NDCG at different K values
- **Regression testing** — run eval in CI, fail on quality drops
- **RAGAS framework** — standardized metrics for RAG pipelines

<br/>

<div class="tip">

**Our trade-off:** LLM-as-judge requires a fast, capable model — with local Qwen3 8B, substring matching gives reliable signal in seconds vs. minutes

</div>

---

![bg fit](./img/bg-title.png)

## **Thank You**
### Questions?
