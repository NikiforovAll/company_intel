# CLAUDE.md

## What This Is

Company Intel — a RAG-based company research assistant. Two-phase system: (1) online data gathering via backoffice agent, (2) offline Q&A via chat agent.

## Architecture

**Polyglot monorepo** orchestrated by .NET Aspire (`src/AppHost/Program.cs`):

```
src/AppHost/   → .NET Aspire orchestrator (Ollama, Qdrant, agent, UI)
src/agent/     → Python FastAPI backend (Pydantic AI agents, AG-UI protocol)
src/ui/        → Next.js 15 frontend (CopilotKit + AG-UI streaming)
```

**Agent backend** (`src/agent/`):
- `main.py` — FastAPI app, two POST endpoints: `/` (chat agent), `/backoffice` (backoffice agent)
- `agent/app.py` — Chat agent: `search_knowledge_base` tool, citation-based answers
- `agent/backoffice.py` — Backoffice agent: `gather_company_data`, `list_gathered_companies`, `delete_company_data`
- `agent/settings.py` — Reads Aspire connection string `ConnectionStrings__ollama-qwen3`, configures Ollama endpoint
- `agent/telemetry.py` — OpenTelemetry via Logfire (HTTP/protobuf for Aspire dashboard, explicit bucket histograms)
- Agents use **AG-UI protocol** via `pydantic_ai.ui.ag_ui.AGUIAdapter` for SSE streaming

**Frontend** (`src/ui/`):
- Tab-based UI: Chat tab (`agentId="agentic_chat"`) and Backoffice tab (`agentId="backoffice_ops"`)
- CopilotKit runtime routes to Python backend via `HttpAgent` (AG-UI client)
- `FixReasoningRole` middleware patches @ag-ui/client bug with reasoning message roles

**Data flow**: UI → CopilotKit → AG-UI HttpAgent → FastAPI → Pydantic AI Agent → Ollama (Qwen3)

### Observability

This project is instrumented with OpenTelemetry (via Logfire).

## Commands

### Run the full stack
```bash
aspire run                          # starts all resources (Ollama, Qdrant, agent, UI)

### Quality gates (all at once)

Always prefer this check instead of running commands one by one.
```bash
.claude/skills/quality-gates/scripts/check.sh          # lint + format + mypy
.claude/skills/quality-gates/scripts/check.sh --all     # + Aspire integration tests
```

### Frontend (src/ui/)
```bash
cd src/ui
pnpm install
pnpm dev                            # Next.js dev server on :3000
```

### .NET Aspire tests
```bash
dotnet test tests/AppHost.Tests -p:WarningLevel=0 /clp:ErrorsOnly
```

### Crawler

To setup crawler (one-time):

```bash
cd src/agent && uv run crawl4ai-setup  # one-time setup for Crawl4AI 
```


## Key Tech Choices

| Layer | Choice | Notes |
|-------|--------|-------|
| LLM | Qwen3 8B via Ollama | 32K context, local-only at query time |
| Embeddings | snowflake-arctic-embed-s | 384-dim, via sentence-transformers (planned) |
| Vector store | Qdrant | Hybrid search (dense + BM25), RRF fusion (planned) |
| Agent framework | Pydantic AI | AG-UI protocol for streaming |
| UI framework | CopilotKit + Next.js 15 | React 19, Tailwind CSS 4 |
| Orchestration | .NET Aspire | Service discovery, OTel dashboard |
| Scraping | Crawl4AI | Planned for Phase 1 |

## Documentation

Design docs live in `docs/` — see `docs/CLAUDE.md` for the full index. Key files:
- `docs/SPEC.md` — original task specification
- `docs/requirements.md` — FR/NFR requirements
- `docs/constraints.md` — pipeline stage bounds
- `docs/roadmap.md` — phased implementation plan
- `docs/data-strategy.md` — data model, chunking, retrieval flow
