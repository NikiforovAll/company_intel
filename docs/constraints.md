# Processing & Embedding Constraints

Explicit bounds for each stage of the pipeline. These are not aspirational — they are hard constraints the implementation must respect.

## 1. Scraping Constraints

| Constraint            | Value                           | Rationale                                             |
| --------------------- | ------------------------------- | ----------------------------------------------------- |
| Max pages per source  | 20                              | Bound crawl depth, avoid scraping entire sites        |
| Max raw document size | 100 KB (text)                   | Discard overly long pages — likely not useful content |
| Request timeout       | 30s per page                    | Fail fast on slow/unresponsive hosts                  |
| Rate limit            | 1 req/s per domain              | Respectful scraping, avoid IP bans                    |
| Retry policy          | 3 attempts, exponential backoff | Transient failures only                               |
| Robots.txt            | Respect always                  | Ethical and legal compliance                          |
| Output format         | Markdown (UTF-8)                | Consistent input for chunking pipeline                |
| Allowed content types | text/html only                  | Skip PDFs, images, videos in POC                      |

## 2. Text Cleaning Constraints

| Constraint          | Value                                     | Rationale                             |
| ------------------- | ----------------------------------------- | ------------------------------------- |
| Remove boilerplate  | nav, footer, sidebar, cookie banners, ads | Noise reduces retrieval quality       |
| Strip HTML tags     | All (keep structure as Markdown)          | Embeddings work on plain text         |
| Min document length | 50 characters after cleaning              | Skip near-empty pages                 |
| Max document length | 50,000 characters                         | Truncate to avoid processing outliers |
| Encoding            | UTF-8, normalize unicode (NFC)            | Consistent tokenization               |
| Language filter     | English only — discard non-English pages  | Embedding model is English-optimized  |

## 3. Chunking Constraints

| Constraint          | Value                                                            | Rationale                                                 |
| ------------------- | ---------------------------------------------------------------- | --------------------------------------------------------- |
| Strategy            | Semantic (heading/paragraph boundaries)                          | Preserve meaning units                                    |
| Target chunk size   | 256–512 tokens                                                   | Fits embedding model context window (512 max)             |
| Hard max chunk size | 512 tokens                                                       | Exceeding model context degrades embedding quality        |
| Min chunk size      | 50 tokens                                                        | Chunks below this are too sparse for meaningful retrieval |
| Overlap             | 50 tokens between adjacent chunks                                | Context continuity at boundaries                          |
| Split hierarchy     | H1 > H2 > H3 > paragraph > sentence                              | Prefer higher-level breaks                                |
| Metadata preserved  | source_url, company, source_type, title, chunk_index, scraped_at | Required for citation and filtering                       |

## 4. Embedding Constraints

| Constraint       | Value                      | Rationale                                        |
| ---------------- | -------------------------- | ------------------------------------------------ |
| Model            | `snowflake-arctic-embed-s` | 384-dim, retrieval-optimized, 51.98 MTEB nDCG@10 |
| Max input tokens | 512                        | Model hard limit — chunks must not exceed        |
| Dimensionality   | 384                        | Fixed by model choice                            |
| Normalization    | L2-normalize vectors       | Required for cosine similarity                   |
| Batch size       | 64 chunks                  | Balance throughput vs memory                     |
| Device           | CPU (GPU optional)         | Must work on consumer hardware without GPU       |
| Deterministic    | Same text → same embedding | Required for reproducible chunk IDs              |

## 5. Vector Store Constraints

| Constraint              | Value                                 | Rationale                              |
| ----------------------- | ------------------------------------- | -------------------------------------- |
| Store                   | Qdrant                                | Pre-search filtering, hybrid search, Aspire integration |
| Distance metric         | Cosine similarity                     | Standard for normalized embeddings     |
| Vectors                 | Dense (384-dim) + Sparse (BM25)       | Hybrid search via RRF fusion           |
| Collection              | Single collection, filter by metadata | Simpler than per-company collections   |
| Chunk ID                | `sha256(url + chunk_index)`           | Deterministic, dedup-friendly          |
| Metadata fields indexed | `company`, `source_type`              | Required for filtered queries          |
| Max collection size     | 100K chunks (POC)                     | Qdrant handles this easily             |

## 6. Retrieval Constraints

| Constraint           | Value                               | Rationale                                  |
| -------------------- | ----------------------------------- | ------------------------------------------ |
| Top-k                | 8–10 chunks per query               | 32K context allows more chunks than 8K did |
| Filter               | Optional `company` filter, inferred by LLM from context | Narrows scope when single company; omitted for cross-company queries |
| Similarity threshold | 0.45 minimum cosine similarity       | Discard irrelevant results                 |
| Context budget       | ≤ 4,000 tokens total retrieved text | Comfortable within 32K context window      |

## 7. Generation Constraints

| Constraint           | Value                                                  | Rationale                                       |
| -------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| LLM                  | Qwen3 8B (Q4_K_M) via Ollama                           | Best reasoning at 8B size, 32K context          |
| LLM context window   | 32,768 tokens (qwen3 8B)                               | 4x previous budget, eliminates context pressure |
| System prompt        | ≤ 500 tokens                                           | Fixed overhead                                  |
| Retrieved context    | ≤ 4,000 tokens                                         | From retrieval stage                            |
| Conversation history | ≤ 4,000 tokens (sliding window)                        | ~6-8 turns                                      |
| Generation headroom  | ≥ 3,000 tokens                                         | For the model's response                        |
| Token budget check   | system + context + history + headroom ≤ context_window | Enforced before every call                      |
| Temperature          | 0.1–0.45                                                | Factual answers, low creativity                 |
| Grounding            | Answer ONLY from retrieved context                     | Hallucination prevention                        |
| Citation             | Every claim must reference source URL                  | Traceability                                    |
