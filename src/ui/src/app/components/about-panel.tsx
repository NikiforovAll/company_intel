"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

const FLOW_DIAGRAM = `graph LR
    subgraph UI["Frontend"]
        Chat["Next.js + CopilotKit"]
    end

    subgraph Scrape["Web Scraping"]
        Crawl["Crawl4AI"]
        Clean["Clean to Markdown"]
    end

    subgraph Process["Processing"]
        Chunk["Chunking 256-512 tok"]
        Embed["arctic-embed-s + BM25"]
    end

    subgraph Agent["Pydantic AI Agent"]
        Ingest["Ingest Tools"]
        Retrieval["Retrieval Tools"]
    end

    subgraph DB["Database"]
        Qdrant[("Qdrant Hybrid RRF")]
    end

    subgraph Inference["Inference"]
        Retrieve["RRF fusion"]
        LLM["Qwen3 8B 32K"]
    end

    Chat -->|SSE| Agent
    Ingest --> Crawl
    Crawl --> Clean
    Clean --> Chunk
    Chunk --> Embed
    Embed --> Qdrant

    Retrieval --> Retrieve
    Retrieve --> Qdrant
    Retrieve --> LLM
    LLM -->|citations| Chat

    style UI fill:#e1f5ff,stroke:#90caf9
    style Agent fill:#fff3e0,stroke:#ffcc80
    style Scrape fill:#f3e5f5,stroke:#ce93d8
    style Process fill:#e8f5e9,stroke:#a5d6a7
    style DB fill:#fce4ec,stroke:#ef9a9a
    style Inference fill:#ffe0b2,stroke:#ffb74d`;

const techDecisions = [
  { component: "LLM", choice: "Qwen3 8B via Ollama", why: "32K context, best reasoning at 8B size, runs locally" },
  { component: "Embeddings", choice: "snowflake-arctic-embed-s", why: "Top MTEB retrieval score (51.98), 384-dim, CPU-fast" },
  { component: "Vector Store", choice: "Qdrant", why: "Pre-search filtering, hybrid RRF, Aspire integration" },
  { component: "Scraper", choice: "Crawl4AI", why: "Native Markdown output, JS rendering, boilerplate removal" },
  { component: "Agent Framework", choice: "Pydantic AI", why: "AG-UI protocol for vendor-neutral SSE streaming" },
  { component: "UI", choice: "CopilotKit + Next.js 15", why: "Production-ready chat components, React 19" },
  { component: "Orchestration", choice: ".NET Aspire", why: "Polyglot service discovery, built-in OTel dashboard" },
];

const principles = [
  { name: "Offline-First", desc: "Retrieval phase needs zero internet" },
  { name: "Reproducibility", desc: "Deterministic chunk IDs, raw files preserved" },
  { name: "Citations Everywhere", desc: "Every chunk carries URL + title, every answer references sources" },
  { name: "Grounding", desc: 'System prompt enforces "answer ONLY from retrieved context"' },
  { name: "Open Standards", desc: "AG-UI, OpenTelemetry, Aspire (all open-source)" },
];

function MermaidDiagram({ id, chart }: { id: string; chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState("");

  useEffect(() => {
    let cancelled = false;
    mermaid.initialize({
      startOnLoad: false,
      theme: "neutral",
      flowchart: { curve: "basis", padding: 24, nodeSpacing: 50, rankSpacing: 60 },
    });
    mermaid
      .render(id, chart)
      .then(({ svg }) => {
        if (!cancelled) setSvg(svg);
      })
      .catch((err) => console.error("Mermaid render error:", err));
    return () => {
      cancelled = true;
    };
  }, [id, chart]);

  if (!svg) return null;

  return (
    <div
      ref={ref}
      className="overflow-auto [&_svg]:mx-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export function AboutPanel() {
  return (
    <div className="h-[calc(100vh-3.5rem)] w-screen overflow-y-auto bg-gray-50 px-8 py-6">
      <div className="mx-auto max-w-[95vw] space-y-6">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Architecture Overview
          </h2>
          <MermaidDiagram id="flow-diagram" chart={FLOW_DIAGRAM} />
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Two-Phase Architecture</h2>
          <div className="space-y-3 text-sm text-gray-700">
            <p>
              <span className="font-semibold text-gray-900">Phase 1 — Ingest (Online):</span>{" "}
              The backoffice agent scrapes public sources via Crawl4AI (website pages, Wikipedia, news),
              cleans HTML to Markdown, chunks semantically (256-512 tokens), embeds with
              snowflake-arctic-embed-s (384-dim) + BM25 sparse vectors, and stores everything in Qdrant.
            </p>
            <p>
              <span className="font-semibold text-gray-900">Phase 2 — Retrieval (Offline):</span>{" "}
              The chat agent embeds the user&apos;s question, runs hybrid retrieval (dense + BM25 via RRF
              fusion), filters by company, and feeds the top chunks (&le;4K tokens) to Qwen3 8B for a
              grounded, citation-backed answer. Zero internet needed at query time.
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Key Technology Decisions</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="pb-2 pr-4 font-medium">Component</th>
                  <th className="pb-2 pr-4 font-medium">Choice</th>
                  <th className="pb-2 font-medium">Why</th>
                </tr>
              </thead>
              <tbody>
                {techDecisions.map((d) => (
                  <tr key={d.component} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-semibold text-gray-900 whitespace-nowrap">{d.component}</td>
                    <td className="py-2 pr-4 text-gray-700 whitespace-nowrap">{d.choice}</td>
                    <td className="py-2 text-gray-600">{d.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Design Principles</h2>
          <ul className="space-y-2 text-sm">
            {principles.map((p) => (
              <li key={p.name} className="flex gap-2">
                <span className="font-semibold text-gray-900 whitespace-nowrap">{p.name}</span>
                <span className="text-gray-400">—</span>
                <span className="text-gray-600">{p.desc}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
