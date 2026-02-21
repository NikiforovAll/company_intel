# Setup Requirements

## Hardware

### Memory Requirements by Component

| Component              | Model/Config                    | RAM     | VRAM     | Disk     |
| ---------------------- | ------------------------------- | ------- | -------- | -------- |
| **Ollama (LLM)**       | Qwen3 8B Q4_K_M                 | 8 GB    | ~5.6 GB  | ~5 GB    |
| **Embeddings**         | snowflake-arctic-embed-s        | ~130 MB | — (CPU)  | ~130 MB  |
| **Qdrant**             | ~10K chunks, dense + sparse     | ~50 MB  | —        | ~100 MB  |
| **Crawl4AI**           | Playwright browser              | ~500 MB | —        | —        |
| **Aspire + Dashboard** | .NET runtime                    | ~200 MB | —        | —        |

### Minimum System Requirements

| Setup             | RAM   | VRAM | Notes                                      |
| ----------------- | ----- | ---- | ------------------------------------------ |
| **GPU inference** | 8 GB  | 6 GB | Recommended: 16 GB RAM + 8 GB VRAM         |
| **CPU-only**      | 16 GB | —    | Recommended: 32 GB. 5-10x slower inference |

> KV cache grows with context length — 8B model at 32K context adds ~2-4 GB VRAM.
> Q4_K_M quantization is the sweet spot for consumer hardware.

## Software Prerequisites

| Tool                                      | Version | Purpose                      |
| ----------------------------------------- | ------- | ---------------------------- |
| [.NET SDK](https://dotnet.microsoft.com/) | 9.0+    | Aspire AppHost               |
| [Python](https://www.python.org/)         | 3.10+   | Agent backend                |
| [uv](https://docs.astral.sh/uv/)          | latest  | Python dependency management |
| [Docker](https://www.docker.com/)         | latest  | Ollama + Qdrant containers   |
| [Node.js](https://nodejs.org/) + pnpm     | 20+     | CopilotKit UI frontend       |
| [Ollama](https://ollama.com/)             | latest  | Local LLM inference          |

## Python Dependencies

```txt
pydantic-ai-slim[ag-ui]
fastapi
uvicorn
qdrant-client
sentence-transformers
crawl4ai
logfire
opentelemetry-distro
opentelemetry-exporter-otlp-proto-grpc
opentelemetry-instrumentation-fastapi
```

## .NET Dependencies (AppHost)

```xml
<PackageReference Include="Aspire.Hosting" />
<PackageReference Include="Aspire.Hosting.Python" />
<PackageReference Include="Aspire.Hosting.Qdrant" />
<PackageReference Include="CommunityToolkit.Aspire.Hosting.Ollama" />
```

## Quick Start

```bash
# 1. Clone and navigate
cd company_intel

# 2. Install Python deps
cd src/agent && uv sync && cd ../..

# 3. Pull Ollama model (happens automatically via Aspire, or manually)
ollama pull qwen3

# 4. Run everything
cd src/aspire && dotnet run
```

Aspire starts all services:
- Agent API → `http://localhost:8888`
- CopilotKit UI → `http://localhost:3000`
- Aspire Dashboard → `http://localhost:18888`
