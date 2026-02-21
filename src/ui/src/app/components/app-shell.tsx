"use client";

import { useState } from "react";
import { CopilotKitProvider } from "@copilotkit/react-core/v2";
import { ChatPanel } from "./chat-panel";
import { HelpModal } from "./help-modal";
import { AboutPanel } from "./about-panel";

type Tab = "chat" | "backoffice" | "about";

const tabs: { id: Tab; label: string; activeColor: string }[] = [
  { id: "chat", label: "Chat", activeColor: "text-blue-600 border-blue-600" },
  { id: "backoffice", label: "Backoffice", activeColor: "text-amber-600 border-amber-600" },
];

const chatSuggestions = [
  "What are the most successful companies recently?",
  "Who is PayPal's CEO?",
  "Honney allegations and involvement wiht PayPal",
  "What is Microsoft's business model?",
  "What are the latest new about Figma?",
  "When was Airbnb founded?",
  "How does Google make money?",
  "What are the key products of Apple?"
].map((ex) => ({ title: ex, message: ex }));

const backofficeSuggestions = [
  "List all companies",
  "Gather data about Figma",
  "Add data about PayPal",
  "Get information for Microsoft",
  "Fetch information about Apple",
  "Delete all data for Airbnb",
  "Check scrape status",
  "Retrieve data for Google",
  "Get information about Figma"
].map((ex) => ({ title: ex, message: ex }));

export function AppShell() {
  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [helpOpen, setHelpOpen] = useState(false);

  return (
    <>
      <nav className="h-14 flex items-center gap-6 px-6 border-b border-gray-200 bg-white">
        <button
          onClick={() => setActiveTab("about")}
          className="font-semibold text-gray-800 mr-4 cursor-pointer hover:text-blue-600 transition-colors"
        >
          Company Intelligence
        </button>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-sm pb-0.5 cursor-pointer ${
              activeTab === tab.id
                ? `border-b-2 font-medium ${tab.activeColor}`
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
        <button
          onClick={() => setHelpOpen(true)}
          className="ml-auto w-7 h-7 rounded-full border border-gray-300 text-gray-400 hover:text-gray-600 hover:border-gray-400 text-sm font-medium cursor-pointer transition-colors"
        >
          ?
        </button>
      </nav>

      {helpOpen && activeTab !== "about" && (
        <HelpModal activeTab={activeTab} onClose={() => setHelpOpen(false)} />
      )}

      {activeTab === "about" && <AboutPanel />}

      <CopilotKitProvider runtimeUrl="/api/copilotkit">
        <div className={`h-[calc(100vh-3.5rem)] w-screen flex flex-col bg-gray-50 ${activeTab !== "chat" ? "hidden" : ""}`}>
          <div className="flex-1 min-h-0 px-8 pt-4">
            <ChatPanel
              agentId="agentic_chat"
              welcomeMessage="What company would you like to know about?"
              suggestions={chatSuggestions}
            />
          </div>
          <footer className="border-t border-gray-200 bg-white px-8 py-2">
            <span className="text-xs text-gray-300">
              Answers from stored data only
            </span>
          </footer>
        </div>

        <div className={`h-[calc(100vh-3.5rem)] w-screen flex flex-col bg-gray-50 ${activeTab !== "backoffice" ? "hidden" : ""}`}>
          <div className="flex-1 min-h-0 px-8 pt-4">
            <ChatPanel
              agentId="backoffice_ops"
              welcomeMessage="What data operation would you like to run?"
              suggestions={backofficeSuggestions}
            />
          </div>
          <footer className="border-t border-gray-200 bg-white px-8 py-2">
            <span className="text-xs text-gray-300">
              Gather &middot; Re-gather &middot; Delete &middot; List
            </span>
          </footer>
        </div>
      </CopilotKitProvider>
    </>
  );
}
