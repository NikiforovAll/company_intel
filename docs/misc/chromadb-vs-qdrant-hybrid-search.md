# ChromaDB vs Qdrant for RAG: Hybrid Search Deep Dive (Early 2026)

## TL;DR

| Feature                     | ChromaDB                           | Qdrant                                                              |
| --------------------------- | ---------------------------------- | ------------------------------------------------------------------- |
| Hybrid search (BM25+vector) | Yes (new `Search()` API + `Rrf`)   | Yes (mature, `prefetch` + `FusionQuery`)                            |
| Native BM25                 | Yes, via `SparseVectorIndexConfig` | Yes, via `Qdrant/bm25` model or manual sparse vectors               |
| RRF fusion                  | Built-in `Rrf()` combinator        | Built-in `Fusion.RRF` and `Fusion.DBSF`                             |
| Filtering                   | Basic `where` clauses              | Advanced filterable HNSW (filter during traversal, not post-search) |
| Persistence                 | SQLite + local files / cloud       | Disk-backed, volume-mountable                                       |
| Aspire integration          | No official package                | `Aspire.Hosting.Qdrant` (v13.1+) + `Aspire.Qdrant.Client`           |
| Scaling                     | Single-node                        | Distributed sharding, horizontal scaling                            |
| Best for                    | Prototyping, notebooks, small apps | Production, entity-heavy RAG, filtered search                       |

---

## 1. Why Keyword Search Matters for Entity-Heavy Queries

Semantic (dense vector) search encodes *meaning*, not *exact terms*. This fails for:

- **Proper nouns**: "Nikiforov" -- embeddings don't know that's a name, they encode general context
- **Product codes / SKUs**: "XR-4200-B" has no semantic meaning to an embedding model
- **Domain jargon**: Rare medical/legal terms absent from training vocab get poor representations
- **Acronyms**: "CQRS" semantically drifts toward unrelated concepts

BM25 (Best Matching 25) scores documents by **exact term frequency**, **inverse document frequency** (rare terms score higher), and **document length normalization**. When a user searches "Contoso invoice #INV-2024-0847", BM25 nails the exact match while semantic search returns vaguely related invoice documents.

**Hybrid search = semantic understanding + keyword precision.** This is not optional for production RAG with entity-heavy data.

---

## 2. How Hybrid Search Works (Architecture)

```
User Query
    |
    +---> Dense Embedding Model --> Vector Search --> Ranked List A
    |
    +---> BM25 / Sparse Model ----> Keyword Search --> Ranked List B
    |
    v
  Fusion (RRF / DBSF)
    |
    v
  Merged Ranked Results --> LLM Context
```

### Reciprocal Rank Fusion (RRF)

RRF merges ranked lists without comparing incompatible scores. The formula:

```
RRF_score(doc) = SUM over all rankers: 1 / (k + rank_i(doc))
```

Where `k` is typically 60. A document ranked #1 in both lists gets `1/61 + 1/61 = 0.0328`. A document ranked #1 in one and #5 in the other gets `1/61 + 1/65 = 0.0318`. Consensus across rankers is rewarded.

Key property: **no score normalization needed** -- only rank positions matter, so you can safely combine BM25 scores (unbounded floats) with cosine similarity (0-1 range).

---

## 3. Qdrant Hybrid Search -- Complete Code

### Setup

```bash
# Docker
docker pull qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant

# Python client
pip install qdrant-client
```

### Create Collection with Dense + Sparse Vectors

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

client.create_collection(
    collection_name="company_docs",
    vectors_config={
        "dense": models.VectorParams(
            distance=models.Distance.COSINE,
            size=384,  # all-MiniLM-L6-v2 output dim
        ),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            modifier=models.Modifier.IDF  # enable IDF weighting for BM25
        )
    }
)
```

### Upsert Documents (Both Vector Types)

```python
import uuid

documents = [
    "Contoso Ltd signed contract #CTR-2024-0091 for Azure migration services.",
    "The quarterly revenue report shows 15% growth in EMEA region.",
    "Invoice #INV-2024-0847 was issued to Nikiforov Consulting on Jan 15.",
    "Machine learning pipeline uses ONNX runtime for inference optimization.",
]

# Qdrant Cloud Inference handles embedding automatically via model name
client.upsert(
    collection_name="company_docs",
    points=[
        models.PointStruct(
            id=uuid.uuid4().hex,
            vector={
                "dense": models.Document(
                    text=doc,
                    model="sentence-transformers/all-MiniLM-L6-v2",
                ),
                "sparse": models.Document(
                    text=doc,
                    model="Qdrant/bm25",
                ),
            },
            payload={"text": doc, "source": "internal"},
        )
        for doc in documents
    ]
)
```

> **Note**: The `models.Document` approach uses Qdrant's server-side inference (Cloud or with configured inference endpoint). For self-hosted without inference, you compute embeddings client-side and pass raw vectors/sparse vectors directly.

### Hybrid Search with RRF

```python
def hybrid_search(query: str, limit: int = 5) -> list:
    """Combine BM25 keyword + dense semantic search via RRF."""
    results = client.query_points(
        collection_name="company_docs",
        prefetch=[
            # Branch 1: Sparse/keyword search
            models.Prefetch(
                query=models.Document(text=query, model="Qdrant/bm25"),
                using="sparse",
                limit=20,
            ),
            # Branch 2: Dense/semantic search
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="sentence-transformers/all-MiniLM-L6-v2",
                ),
                using="dense",
                limit=20,
            ),
        ],
        # Fuse the two ranked lists
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=limit,
    )
    return results.points


# Entity-heavy query -- BM25 catches the exact invoice number
results = hybrid_search("invoice INV-2024-0847 Nikiforov")
for r in results:
    print(f"Score: {r.score:.4f} | {r.payload['text'][:80]}")
```

Qdrant also supports `Fusion.DBSF` (Distribution-Based Score Fusion) which normalizes scores into a shared distribution before combining -- useful when you want score-aware fusion rather than rank-only.

### Manual Sparse Vectors (Self-Hosted, No Inference)

```python
from qdrant_client.models import SparseVector, PointStruct

# Compute sparse vectors yourself (e.g., via rank_bm25 or SPLADE)
client.upsert(
    collection_name="company_docs",
    points=[
        PointStruct(
            id=1,
            vector={
                "dense": [0.12, -0.34, ..., 0.56],  # 384-dim from your model
                "sparse": SparseVector(
                    indices=[331, 14136, 50021],  # vocab token IDs
                    values=[0.5, 0.7, 0.3],       # term weights
                ),
            },
            payload={"text": "..."},
        )
    ]
)
```

---

## 4. ChromaDB Hybrid Search -- Complete Code

ChromaDB added sparse vector support (BM25 + SPLADE) with a new `Search()` API. No breaking changes to existing collections.

### Setup

```bash
pip install chromadb
```

### Create Collection with BM25 Index

```python
import chromadb
from chromadb import Schema, SparseVectorIndexConfig, Bm25EmbeddingFunction, K

client = chromadb.Client()  # or chromadb.PersistentClient(path="./chroma_data")

schema = Schema().create_index(
    key="sparse_vector_key",
    config=SparseVectorIndexConfig(
        embedding_function=Bm25EmbeddingFunction(avg_len=10),
        source_key=K.DOCUMENT,
        bm25=True,
    ),
)

collection = client.get_or_create_collection(
    "company_docs",
    schema=schema,
)
```

### Add Documents

```python
collection.upsert(
    ids=["doc1", "doc2", "doc3"],
    documents=[
        "Contoso Ltd signed contract #CTR-2024-0091 for Azure migration.",
        "Quarterly revenue report shows 15% growth in EMEA region.",
        "Invoice #INV-2024-0847 issued to Nikiforov Consulting Jan 15.",
    ],
)
```

### Hybrid Search with RRF

```python
from chromadb import Search, K, Knn, Rrf

# Two retrieval branches
dense_rank = Knn(
    query="invoice INV-2024-0847 Nikiforov",
    return_rank=True,
    limit=200,
)

sparse_rank = Knn(
    query="invoice INV-2024-0847 Nikiforov",
    key="sparse_vector_key",
    return_rank=True,
    limit=200,
)

# Fuse with weighted RRF
hybrid_rank = Rrf(
    ranks=[dense_rank, sparse_rank],
    weights=[0.7, 0.3],  # lean toward semantic, but keyword gets a vote
    k=60,
)

search = (
    Search()
    .where(K("source") == "internal")  # metadata filter
    .rank(hybrid_rank)
    .limit(10)
    .select(K.DOCUMENT, K.SCORE, "source")
)

results = collection.search(search)
```

### BM25-Only Search (Keyword Sidecar Pattern)

Before ChromaDB had native sparse support, people ran BM25 separately:

```python
# Legacy pattern (still useful to understand)
from rank_bm25 import BM25Okapi

corpus = [doc.page_content for doc in documents]
tokenized = [doc.split() for doc in corpus]
bm25 = BM25Okapi(tokenized)

# Get BM25 scores
bm25_scores = bm25.get_scores(query.split())

# Get ChromaDB vector results
chroma_results = collection.query(query_texts=[query], n_results=20)

# Manual RRF fusion
def reciprocal_rank_fusion(ranked_lists, k=60):
    fused = {}
    for ranked_list in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked_list):
            fused[doc_id] = fused.get(doc_id, 0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)
```

**This legacy pattern is no longer needed** with ChromaDB's native `Rrf` combinator, but it shows how RRF works mechanically.

---

## 5. Qdrant Setup and Operations

### Docker (One-liner)

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant
```

Port 6333 = REST API, 6334 = gRPC (faster for bulk ops). Data persists in the mounted volume.

### Dashboard

Qdrant ships with a built-in web UI at `http://localhost:6333/dashboard` -- collection browser, query tester, cluster status.

### Python Client

```bash
pip install qdrant-client
```

```python
from qdrant_client import QdrantClient

# Remote
client = QdrantClient(url="http://localhost:6333")

# In-memory (testing, no Docker needed)
client = QdrantClient(":memory:")

# Local on-disk (no Docker needed, similar to ChromaDB experience)
client = QdrantClient(path="./qdrant_local")
```

The `path=` mode gives you ChromaDB-level simplicity -- no Docker, no server, just a directory. Good for prototyping.

### Ease of Setup Verdict

ChromaDB is still simpler for zero-config local dev (`pip install chromadb` and go). Qdrant is nearly as easy with the `path=` mode, and the Docker setup is one command. For production, Qdrant's Docker/k8s story is more mature.

---

## 6. Qdrant with .NET Aspire

There is a **first-party Aspire integration** -- no need for `AddContainer` workarounds.

### AppHost (orchestrator)

```xml
<PackageReference Include="Aspire.Hosting.Qdrant" Version="13.1.0" />
```

```csharp
var builder = DistributedApplication.CreateBuilder(args);

var qdrant = builder.AddQdrant("qdrant")
    .WithLifetime(ContainerLifetime.Persistent);

builder.AddProject<Projects.ApiService>("apiservice")
    .WaitFor(qdrant)
    .WithReference(qdrant);
```

### Client Project

```xml
<PackageReference Include="Aspire.Qdrant.Client" Version="9.4.2" />
```

```csharp
// In Program.cs
builder.AddQdrantClient(connectionName: "qdrant");

// In your service
public class EmbeddingService(QdrantClient client)
{
    public async Task SearchAsync(float[] queryVector)
    {
        var results = await client.QueryAsync(
            collectionName: "company_docs",
            query: queryVector,
            limit: 10
        );
    }
}
```

The Aspire integration handles: container lifecycle, health checks, API key generation, connection string injection, and the Qdrant dashboard is accessible through the Aspire dashboard's resource links.

---

## 7. Feature Comparison at <100K Vectors

| Dimension                | ChromaDB                                         | Qdrant                                                                                           |
| ------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| **Insert speed**         | Fast (Rust-core rewrite, 4x improvement in 2025) | Fast                                                                                             |
| **Query latency <100K**  | Sub-millisecond                                  | Sub-millisecond                                                                                  |
| **Filtering**            | Post-search `where` clauses                      | **Pre-search filterable HNSW** (filters applied during graph traversal -- more accurate results) |
| **Hybrid search**        | New `Search()` API with `Rrf`                    | Mature `prefetch` + `FusionQuery` API                                                            |
| **Multi-vector per doc** | Not native                                       | Yes (e.g., title vector + body vector per point)                                                 |
| **Quantization**         | Basic                                            | Scalar, binary, product quantization; asymmetric (24x compression)                               |
| **API surface**          | Python-first, simple CRUD                        | REST + gRPC + Python + Rust + Go + Java + C# clients                                             |
| **Clustering**           | Single-node only                                 | Distributed sharding + replication                                                               |
| **Payload indexing**     | Basic metadata                                   | Rich payload indexes (keyword, integer, geo, datetime, full-text)                                |
| **On-disk index**        | Yes                                              | Yes, fine-grained control (vectors on disk, index in RAM, etc.)                                  |

### At <100K vectors, both are fast enough. The differentiators are:

1. **Filtering quality**: Qdrant's filterable HNSW gives correct results when combining similarity search + metadata filters. ChromaDB applies filters post-search, which can return fewer results than requested.
2. **Hybrid search maturity**: Qdrant's prefetch/fusion API is battle-tested. ChromaDB's `Search()` API is newer.
3. **Aspire story**: Qdrant has official packages. ChromaDB does not.
4. **Multi-vector**: If you want separate vectors for title/body/summary per document, only Qdrant supports this natively.

---

## 8. Recommendation

For a .NET Aspire-based RAG system with entity-heavy data:

**Use Qdrant.** The reasoning:
- First-party Aspire hosting (`Aspire.Hosting.Qdrant`)
- Mature hybrid search with server-side BM25 + dense fusion
- Filterable HNSW for accurate filtered search
- Multi-vector support for different document sections
- `QdrantClient(path="./local")` for dev parity with ChromaDB simplicity
- Production-ready clustering when you need to scale

ChromaDB remains excellent for quick prototypes and notebooks where you want zero setup friction.

---

## Sources

- [ChromaDB Sparse Vector Support](https://www.trychroma.com/project/sparse-vector-search)
- [ChromaDB BM25 Feature Request (GitHub #1686)](https://github.com/chroma-core/chroma/issues/1686)
- [Qdrant Hybrid Search Article](https://qdrant.tech/articles/hybrid-search/)
- [Qdrant Hybrid Search Demo (Course)](https://qdrant.tech/course/essentials/day-3/hybrid-search-demo/)
- [Qdrant Sparse Vectors Explained](https://qdrant.tech/articles/sparse-vectors/)
- [Qdrant BM42 Article](https://qdrant.tech/articles/bm42/)
- [Qdrant Quickstart](https://qdrant.tech/documentation/quickstart/)
- [Aspire.Hosting.Qdrant (NuGet)](https://www.nuget.org/packages/Aspire.Hosting.Qdrant)
- [Aspire.Qdrant.Client (NuGet)](https://www.nuget.org/packages/Aspire.Qdrant.Client)
- [Aspire Qdrant Get Started](https://aspire.dev/integrations/databases/qdrant/qdrant-get-started/)
- [Chroma vs Qdrant Comparison (Aloa)](https://aloa.co/ai/comparisons/vector-database-comparison/chroma-vs-qdrant)
- [Chroma DB vs Qdrant Key Differences (Airbyte)](https://airbyte.com/data-engineering-resources/chroma-db-vs-qdrant)
- [RRF for Hybrid Search (Azure)](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)
- [RRF Explained (Medium)](https://medium.com/@devalshah1619/mathematical-intuition-behind-reciprocal-rank-fusion-rrf-explained-in-2-mins-002df0cc5e2a)
