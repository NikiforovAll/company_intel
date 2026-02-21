# Chunking, Embedding & Ingestion Pipeline

## Pipeline Flow

```
artifacts/data/{company}/raw/*.md
    → load_raw_documents()          # parse YAML frontmatter + body
    → chunk_documents()             # semantic chunking (target 256, max 384 tokens)
    → embedder.embed_texts()        # dense (Ollama) + sparse (fastembed)
    → vectorstore.upsert_chunks()   # batch upsert to Qdrant
```

## Module Structure

### `agent/chunker/`
- `config.py` — target 256 tokens, hard max 384, min 50, overlap 50
- `models.py` — `Chunk`, `ChunkMetadata` (Pydantic models)
- `pipeline.py` — semantic chunking: split by headings → paragraphs → sentences → greedy merge → overlap

### `agent/embedder/`
- `config.py` — sparse model `Qdrant/bm25`, batch size 64, dense dim 384
- `pipeline.py` — `EmbedderService`: Ollama HTTP for dense, fastembed for sparse BM25

### `agent/vectorstore/`
- `config.py` — collection `company_intel`, batch size 100
- `client.py` — `VectorStoreService`: Qdrant client with auto-collection creation, payload indexes on `company` and `source_type`

## Integration Points

### Backoffice Pipeline (`agent/backoffice.py`)
After `scrape_company()` succeeds, `_ingest_to_vectorstore()` runs:
1. Delete existing vectors for the company (idempotent re-gather)
2. Load raw documents from disk
3. Chunk documents
4. Embed (dense + sparse)
5. Upsert to Qdrant

### Delete Operation
`delete_company_data` tool also calls `store.delete_company()` to wipe vectors.

### Eager Loading (`main.py`)
BM25 model pre-loaded in FastAPI lifespan to avoid cold-start on first ingestion.

## Configuration

Connection strings from Aspire:
- `ConnectionStrings__ollama-qwen3` — LLM model
- `ConnectionStrings__ollama-snowflake-arctic-embed` — embedding model (Aspire strips the `:33m` tag from the resource name)
- `ConnectionStrings__qdrant_http` — vector store HTTP endpoint (preferred over `ConnectionStrings__qdrant` which is gRPC)

Format: `Endpoint=http://host:port;Key=apikey;Model=model-name`

## Qdrant Collection Schema

Collection: `company_intel`
- Dense vector: `dense` (384-dim, cosine)
- Sparse vector: `sparse` (BM25)
- Payload indexes: `company` (keyword), `source_type` (keyword)
- Point ID: UUID derived from SHA-256 of `url::chunk_index` (Qdrant requires UUID or integer IDs)

## Lessons Learned

### Aspire Connection Strings

Aspire generates connection string env vars from resource names. For Ollama model resources, the resource name is `ollama-{model-name}` with the tag stripped. So `snowflake-arctic-embed:33m` becomes `ConnectionStrings__ollama-snowflake-arctic-embed` — not `...-33m`.

Aspire's Qdrant integration exposes two connection strings:
- `ConnectionStrings__qdrant` — gRPC endpoint (not usable with `QdrantClient(url=...)` default HTTP mode)
- `ConnectionStrings__qdrant_http` — HTTP REST endpoint (use this one)

### Ollama Embed API

- Endpoint: `POST /api/embed` (not `/api/embeddings` which is the legacy single-input endpoint)
- Request: `{"model": "...", "input": ["text1", "text2"], "truncate": true}`
- Response: `{"embeddings": [[...], [...]]}`
- The `truncate: true` flag is important — without it, Ollama returns 400 if any input exceeds the model's context window

### Embedding Model Context Limit

`snowflake-arctic-embed:33m` is a BERT model with a **512-token context window** (its own BPE tokenizer, not tiktoken). Our chunker uses tiktoken `cl100k_base` which counts differently from the model's tokenizer. A chunk that's 400 tiktoken tokens might be 550+ in the model's tokenizer.

**Solution**: target 256, hard max 384 tiktoken tokens (conservative margin), plus `truncate: true` in the embed request as a safety net. This ensures chunks always fit within the model's 512-token limit regardless of tokenizer differences.

### Qdrant Point IDs

Qdrant only accepts **unsigned integers** or **UUIDs** as point IDs. Raw SHA-256 hex digests (64 chars) are neither. We derive a UUID from the first 16 bytes of the SHA-256 hash: `uuid.UUID(bytes=sha256(key)[:16])`.
