# Embedding Runtime

## Decision

- **Dense embeddings**: Ollama (`snowflake-arctic-embed:33m`) — 384-dim, cosine similarity
- **Sparse BM25**: fastembed (`Qdrant/bm25`) — ~10MB ONNX model
- **Token counting**: tiktoken (`cl100k_base`) — chunk boundary precision

## Why Ollama for Dense Embeddings

| Factor | Ollama | sentence-transformers |
|--------|--------|-----------------------|
| Runtime | Already orchestrated via Aspire | Requires PyTorch (~2GB) |
| Model loading | Shared with LLM inference | Separate process |
| API | HTTP `/api/embed` | Python in-process |
| Deployment | Single container | Extra dependency |

Ollama already runs for LLM inference (Qwen3). Adding an embedding model (`snowflake-arctic-embed:33m`, 384-dim) reuses the same runtime — no PyTorch, no GPU contention, no extra container.

**Caveat**: The Ollama `/api/embed` endpoint requires `truncate: true` to handle inputs exceeding the model's 512-token BERT context window. Without it, Ollama returns HTTP 400 for oversized inputs instead of silently truncating.

## Why fastembed for BM25 Only

Ollama doesn't support sparse vector generation. fastembed provides `Qdrant/bm25` as a lightweight ONNX model (~10MB). It runs CPU-only, loads in <1s, and produces sparse vectors compatible with Qdrant's native sparse vector support.

Alternative: manual BM25 via rank_bm25 or sklearn TfidfVectorizer. fastembed is preferred because it produces Qdrant-compatible sparse vectors directly and handles tokenization consistently.

## Why tiktoken for Token Counting

Chunk boundaries need precise token counts (target 256, hard max 384). Options:

- **tiktoken** (`cl100k_base`): exact BPE tokenizer, fast C extension, ~0.1ms per count
- **len(text.split())**: whitespace approximation, ~30% error on technical text
- **Model-specific tokenizer**: ties chunking to embedding model, unnecessary coupling

tiktoken provides accurate counts without depending on the embedding model's tokenizer.

**Important**: tiktoken `cl100k_base` and the model's BERT tokenizer produce different token counts for the same text. A chunk at 384 tiktoken tokens may exceed 512 in the model's tokenizer. The conservative chunk size (256 target, 384 max) plus `truncate: true` ensures no data loss.
