# Critique: Devil's Advocate

Honest assessment of weaknesses, blind spots, and questionable assumptions in the current design.

---

## ~~1. The "Offline" Constraint Is Artificial and Self-Defeating~~ — ACCEPTED

**Status: Accepted constraint.** This is an explicit spec requirement — offline query phase is non-negotiable. We accept the tradeoffs (weaker LLM, local embeddings) as the cost of compliance. Mitigated by choosing the best local models available (Qwen3 8B, snowflake-arctic-embed-s).

---

## 2. Scraping Strategy Is Naively Optimistic

The plan assumes we can reliably scrape company websites, Wikipedia, Crunchbase, and news. Reality:

- **Crunchbase blocks scrapers aggressively.** Rate limiting, CAPTCHAs, login walls. Crawl4AI won't help. This is a known, unsolved problem — Crunchbase data requires their API ($).
- **Company websites are wildly inconsistent.** Some are 5-page brochures, others are 10,000-page enterprises. Our "max 20 pages" cap is arbitrary — we'll get the homepage and 19 random subpages, missing the actual useful content (investor relations, press releases, about page buried 3 levels deep).
- **News scraping without an API is fragile.** Google News blocks scrapers. News sites have paywalls. We'll get headlines and first paragraphs at best.
- **No crawl prioritization.** We treat all 20 pages equally. The "About Us" page is infinitely more valuable than the cookie policy, but we have no way to express this.

**The hard question:** For how many companies will the gather phase actually produce useful, complete data?

---

## 3. Semantic Chunking Is Not What We Think It Is

We chose "semantic chunking" over fixed-size windows. Sounds good. But:

- **We're not doing true semantic chunking.** True semantic chunking uses embeddings to detect topic shifts (sentence-transformers + cosine similarity between adjacent segments). We're doing **structural chunking** — splitting on Markdown headings. These are different things.
- **Markdown structure depends entirely on Crawl4AI's output quality.** If Crawl4AI produces flat Markdown without headings (common for scraped content), our "semantic" chunking degrades to paragraph splitting, which degrades to the recursive character split we rejected.
- **The 512-token target is dictated by the embedding model, not by what's optimal for retrieval.** We chose the model first, then constrained chunking to fit. The tail is wagging the dog. With `nomic-embed-text` (8K context), we could use much larger chunks and potentially better retrieval.

**The hard question:** Have we actually tested chunking quality on real scraped company pages, or are we designing in a vacuum?

---

## ~~4. all-MiniLM-L6-v2 Is a 2021 Model~~ — MITIGATED

**Status: Mitigated.** Switched to `snowflake-arctic-embed-s` — retrieval-optimized, +10 points on MTEB retrieval (51.98 vs ~41), same 384 dims. Residual risk: 384-dim embeddings may still struggle with domain jargon — validate on real data.

---

## ~~5. Vector-Only Search Misses Entity Queries~~ — RESOLVED

**Status: Resolved.** Switched to Qdrant with hybrid search (BM25 + dense vectors via RRF fusion). Entity queries now handled by BM25 branch, semantic queries by dense branch. Pre-search filtering for optional company scoping. See `docs/tradeoffs/04-vector-store.md` and `docs/tradeoffs/05-retrieval.md`.

Company intelligence queries are often **entity-heavy**:
- "When did Spotify go public?"
- "Who is the CEO of Airbnb?"
- "What was Figma's Series C valuation?"

These queries contain specific entities (dates, names, dollar amounts) that vector similarity handles poorly. "CEO" and "Chief Executive Officer" might be close in embedding space, but "Brian Chesky" and "CEO of Airbnb" are not.

**Update:** Both ChromaDB and Qdrant now support hybrid search (BM25 + vector + RRF fusion). The keyword search gap is solvable with either store. The remaining differentiator is **filtering quality** — Qdrant filters during HNSW traversal (pre-search), ChromaDB filters after (post-search). This matters when company filter is applied, though filtering is optional (cross-company queries like "compare Spotify and Airbnb" skip it).

See `docs/tradeoffs/04-vector-store.md` and `docs/misc/chromadb-vs-qdrant-hybrid-search.md` for full analysis.

---

## ~~6. The Context Window Budget Is a House of Cards~~ — RESOLVED

**Status: Resolved.** Switched to Qwen3 8B (32K context). Budget now has ~20K headroom instead of 0. Original analysis below for historical context.

8K tokens total. Our allocation:

| Segment              | Tokens |
| -------------------- | ------ |
| System prompt        | 500    |
| Retrieved chunks     | 3,000  |
| Conversation history | 2,000  |
| Response             | 2,000  |
| Buffer               | 500    |

Problems:
- **3,000 tokens ≈ 5–6 chunks.** For questions that span multiple topics ("Tell me about Spotify's history, business model, and competitors"), 5 chunks is insufficient. The model will give a partial answer and we'll blame retrieval.
- **2,000 tokens of conversation history ≈ 3–4 turns.** Multi-turn conversations will lose context fast. The user asks a follow-up and the model has already forgotten the first question.
- **No room for error.** If one chunk is 600 tokens instead of 300, the budget breaks. We have no graceful degradation — just silent truncation.
- **mistral 7B has 32K context for the same VRAM.** We're choosing llama3 for quality, then crippling that quality with an impossibly tight context window.

**The hard question:** Is llama3-8K actually better than mistral-32K for RAG, when RAG quality is primarily determined by how much context you can feed?

---

## 7. No Evaluation Framework = Flying Blind

We have:
- Detailed constraints (chunk size, top-k, similarity threshold)
- Specific numeric values (0.3 cosine threshold, 512 max tokens, 50-token overlap)

But **none of these numbers are validated.** They're copy-pasted from tutorials and blog posts. We don't have:
- A test set of questions per company
- Ground truth answers to measure against
- Retrieval quality metrics (precision@k, recall@k, MRR)
- End-to-end answer quality assessment
- A way to know if 0.3 threshold is right vs 0.25 or 0.4

We're building an entire pipeline on vibes-based parameter selection.

**The hard question:** Shouldn't evaluation be requirement #1, not an open question saved for later?


---

## Summary: Top Risks

|   #   | Risk                                               | Severity | Likelihood |           Status            |
| :---: | -------------------------------------------------- | :------: | :--------: | :-------------------------: |
|   1   | Offline constraint limits answer quality           |  Medium  |  Certain   | Accepted (spec requirement) |
|   2   | ~~8K context window produces shallow answers~~     |    —     |     —      |    Resolved (Qwen3 32K)     |
|   3   | Scraping fails for key sources (Crunchbase, news)  |   High   |    High    |            Open             |
|   4   | ~~Vector-only search misses entity queries~~         |    —     |     —      | Resolved (Qdrant RRF) |
|   5   | ~~Embedding model too weak for domain vocabulary~~ |   Low    |   Medium   | Mitigated (arctic-embed-s)  |
|   6   | No evaluation → can't measure if anything works    |   High   |  Certain   |            Open             |
|   7   | Analysis paralysis — docs grow, code doesn't       |  Medium  |   Medium   |            Open             |
