"use client";

import { CopilotKitProvider, CopilotChat } from "@copilotkit/react-core/v2";

const examples = [
  "Who are Figma's competitors?",
  "What is Spotify's business model?",
  "When was Airbnb founded?",
  "How does Stripe make money?",
];

export default function Home() {
  return (
    <CopilotKitProvider runtimeUrl="/api/copilotkit">
      <main className="h-[calc(100vh-3.5rem)] w-screen flex flex-col bg-gray-50">
        <div className="flex-1 min-h-0 px-8 pt-4">
          <CopilotChat
            className="h-full rounded-2xl"
            labels={{ welcomeMessageText: "What company would you like to know about?" }}
            agentId="agentic_chat"
          />
        </div>
        <footer className="border-t border-gray-200 bg-white px-8 py-3">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="text-sm font-medium text-gray-400 uppercase tracking-wider mr-1">Try</span>
            {examples.map((ex) => (
              <span
                key={ex}
                className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-full px-4 py-1.5 hover:bg-gray-100 cursor-default transition-colors"
              >
                {ex}
              </span>
            ))}
            <span className="ml-auto text-xs text-gray-300">
              Answers from stored data only
            </span>
          </div>
        </footer>
      </main>
    </CopilotKitProvider>
  );
}
