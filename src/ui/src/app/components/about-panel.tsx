"use client";

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

export function AboutPanel() {
  return (
    <div className="h-[calc(100vh-3.5rem)] w-screen overflow-y-auto bg-gray-50 px-8 py-6">
      <div className="mx-auto max-w-[95vw] space-y-6">
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
