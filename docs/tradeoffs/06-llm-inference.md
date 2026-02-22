# Tradeoff: LLM Inference

## Decision: Ollama with Qwen3 8B (Q4_K_M)

Previously: llama3 8B (8K context). Changed because 8K context was a critical bottleneck — the context budget was a "house of cards" with no room for error. Qwen3 8B provides 32K context + significantly better reasoning at the same VRAM cost.

## Alternatives Considered

| Model | Params | Context | Q4_K_M VRAM | MMLU-Pro | IFEval (strict) | Notes |
|-------|:------:|:------:|:-----------:|:--------:|:---------------:|-------|
| llama3 8B | 8B | 8K | ~5.5 GB | ~44 | ~72 | Previous choice |
| **qwen3 8B** | 8B | 32K | ~5.6 GB | **64.3** | — | Primary choice |
| llama3.1 8B | 8B | 128K | ~6 GB | 48.3 | **75.9** | Fallback |
| qwen2.5 7B | 7B | 128K | ~5.5 GB | 56.3 | 71.2 | Strong but hallucination-prone |
| mistral 7B v0.45 | 7.3B | 32K | ~5.5 GB | 24.5 | ~65 | Outclassed |
| gemma2 9B | 9B | 8K | ~6.5 GB | 52.1 | 70.1 | Good grounding, limited context |
| phi-3.5 mini | 3.8B | 128K | ~3.5 GB | ~48 | ~67 | Too small for complex QA |

## Why Qwen3 8B

**Pros:**
- MMLU-Pro **64.3** — outperforms Qwen2.5-14B (a model twice its size) and every other 8B model
- 32K context — solves the 8K bottleneck. 32K is the practical sweet spot for RAG (research shows models saturate at 4-16K effective usage; 128K is insurance you rarely need)
- Dual-mode: standard for fast extractive QA, reasoning mode for complex synthesis
- ~5.6 GB Q4_K_M — same VRAM budget as llama3
- Available in Ollama: `ollama run qwen3:8b`

**Cons:**
- Newer, less battle-tested than llama3 ecosystem
- IFEval not yet benchmarked — instruction following for grounding instructions needs empirical validation
- 32K vs 128K — if we ever need extremely long context, would need to switch

## Why Not Others

### llama3.1 8B
Best IFEval score (75.9) — most reliable at following grounding instructions. If Qwen3 hallucinates, swap the model string. Not a feature to build — just a human decision.

### mistral 7B v0.45
MMLU-Pro 24.5 — far behind every competitor. No longer competitive at this size class.

### gemma2 9B
Excellent grounding (studies show it "completely eliminated factual hallucinations" in domain tests). But 8K context has the same bottleneck we're escaping. Also slightly larger VRAM (6.5 GB).

### phi-3.5 mini
Only 3.8B params — works for simple extractive QA but struggles with synthesis. Good for constrained hardware only.

### Cloud APIs
Violates offline constraint. Best quality but not acceptable for this project.

## Quantization: Q4_K_M

| Quantization | Size | Quality Loss | Speed |
|:------------|:----:|:------------:|:-----:|
| FP16 | 16 GB | None | Baseline |
| Q8_0 | 8 GB | Negligible | Faster |
| **Q4_K_M** | ~5.6 GB | Small | Fast |
| Q4_0 | ~4.5 GB | Moderate | Fastest |

Q4_K_M remains the sweet spot: significant size reduction, minimal quality impact for factual QA.

## Context Window Budget (32K tokens)

```
┌──────────────────────────────────┐
│ System prompt       ~500         │
│ Retrieved chunks    ~4,000       │  ← was 3,000 (8-10 chunks vs 5-6)
│ Conversation hist.  ~4,000       │  ← was 2,000 (6-8 turns vs 3-4)
│ Response            ~3,000       │  ← was 2,000
│ Buffer              ~500         │
├──────────────────────────────────┤
│ Used               ~12,000       │
│ Available          ~32,000       │
│ Headroom           ~20,000       │  ← was 0 (house of cards)
└──────────────────────────────────┘
```

20K tokens of headroom means: no silent truncation, room for longer conversations, ability to retrieve more chunks when needed. The tight budget was a top risk — now eliminated.

## Why 32K > 128K for RAG

Research findings:
- **"Lost in the Middle"** (Liu et al., Stanford): LLMs attend to beginning and end of context but lose 30%+ accuracy for information in the middle. More context ≠ better answers.
- **Saturation at 4-16K**: Models effectively use only 10-20% of their context window. Beyond saturation, performance degrades.
- **RAG with good retrieval uses 3-6K tokens of context** — even 32K is generous headroom.
- 128K adds VRAM overhead for KV cache at longer contexts — cost without benefit for our use case.

## Prompt Engineering for Grounding

Key system prompt requirements (unchanged):
- "Answer ONLY based on the provided context"
- "If the context doesn't contain the answer, say 'I don't have enough information'"
- "Cite sources using [Source: URL] format"
- "Do not use prior knowledge or make assumptions"

Critical for any 8B model. Testing grounding compliance should be the first evaluation metric.

## When to Switch

All local models are one config change away. No fallback logic needed — just change the model name.

- **→ llama3.1 8B**: if grounding compliance is poor
- **→ gemma3 12B**: if answer quality is unacceptable and GPU budget allows ~8 GB VRAM
- **→ Cloud API**: if offline constraint is relaxed for production
