# Tradeoff: Text Processing & Chunking

## Decisions

1. **Cleaning**: Crawl4AI Markdown output + post-processing normalization
2. **Chunking**: Semantic chunking (heading/paragraph-aware)

## Chunking Strategies Compared

| Strategy                  | Context-Aware | Boundary Quality | Complexity | Chunk Size Control |
| ------------------------- | :-----------: | :--------------: | :--------: | :----------------: |
| **Semantic (chosen)**     |      Yes      |       High       |   Medium   |        Good        |
| Fixed-size token windows  |      No       |       Poor       |    Low     |       Exact        |
| Recursive character split |    Partial    |      Medium      |    Low     |        Good        |
| Sentence-level            |    Partial    |      Medium      |    Low     |      Variable      |
| Document-structure (AST)  |      Yes      |     Highest      |    High    |      Variable      |

## Tradeoffs

### Semantic Chunking (chosen)

Splits on natural boundaries: headings, paragraph breaks, section boundaries. Falls back to sentence boundaries when sections are too long.

**Pros:**
- Preserves meaning units — a chunk about "funding history" stays together
- Heading hierarchy becomes metadata (section context)
- Better retrieval relevance — chunks are topically coherent
- Overlap at boundaries preserves cross-chunk context

**Cons:**
- Chunk sizes vary (some sections are 50 tokens, others 500)
- Requires Markdown structure — garbage in, garbage out
- More complex than fixed-size splitting
- Edge case: very long paragraphs without subheadings need sentence-level fallback

### Fixed-Size Token Windows (rejected)

Split every N tokens regardless of content.

**Pros:** Simple, predictable chunk sizes, no preprocessing needed
**Cons:** Splits mid-sentence, mid-paragraph, mid-thought. Destroys meaning boundaries. Embedding quality degrades because chunks mix unrelated topics.

### Recursive Character Split (rejected — LangChain default)

Split by `\n\n` → `\n` → `. ` → ` ` with a max size.

**Pros:** Better than fixed-size, handles common boundaries
**Cons:** Character-based, not token-based — chunk sizes unpredictable for the embedding model. Doesn't understand Markdown heading hierarchy.

## Text Cleaning Pipeline

```
Raw HTML → Crawl4AI → Markdown → Post-processing → Chunks
```

### Post-Processing Steps

1. **Unicode normalization** (NFC) — consistent tokenization
2. **Whitespace normalization** — collapse multiple newlines, trim
3. **Remove artifacts** — leftover HTML entities, empty links, image alt-text without context
4. **Min-length filter** — discard documents < 100 chars
5. **Max-length truncation** — cap at 50K chars

### Why Markdown as Intermediate Format

| Property                   |          HTML          | Plain Text | Markdown |
| -------------------------- | :--------------------: | :--------: | :------: |
| Preserves structure        |          Yes           |     No     |   Yes    |
| Token-efficient            | No (tags waste tokens) |    Yes     |   Yes    |
| Heading hierarchy          |          Yes           |     No     |   Yes    |
| Easy to chunk semantically |          Hard          |    Hard    |   Easy   |
| Human-readable             |           No           |    Yes     |   Yes    |

Markdown is the best intermediate format for RAG: structure-preserving yet token-efficient.

## Chunk Size: Why 256–512 Tokens

- `all-MiniLM-L6-v2` has a **512 token context window** — exceeding it truncates input silently
- Empirically, 256–512 tokens per chunk balances:
  - **Granularity**: specific enough for precise retrieval
  - **Context**: enough surrounding text for the embedding to capture meaning
  - **Budget**: 5–10 chunks × 300 avg tokens = 1,500–3,000 tokens — fits LLM context

Smaller chunks (< 100 tokens) → too many fragments, lose context
Larger chunks (> 512 tokens) → truncated by embedding model, mix topics

## Overlap: Why 50 Tokens

- Prevents "blind spots" at chunk boundaries
- If a fact spans two paragraphs, overlap ensures at least partial capture in both chunks
- 50 tokens ≈ 1–2 sentences — minimal duplication cost
- No overlap → boundary artifacts in retrieval
- Too much overlap (> 100) → redundant chunks, wasted storage and retrieval budget
