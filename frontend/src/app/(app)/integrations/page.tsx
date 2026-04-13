"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IntegrationCard, Integration } from "@/components/integrations/IntegrationCard";

const ALL_INTEGRATIONS: Integration[] = [
  {
    id: "gmail",
    name: "Gmail",
    icon: "📧",
    description: "Read, send, and manage emails. Agents can draft replies and triage your inbox.",
    status: "connected",
    lastSync: "2 min ago",
    usageCount: 342,
  },
  {
    id: "google-sheets",
    name: "Google Sheets",
    icon: "📊",
    description: "Read and write spreadsheet data. Perfect for structured reporting and data pipelines.",
    status: "connected",
    lastSync: "15 min ago",
    usageCount: 89,
  },
  {
    id: "slack",
    name: "Slack",
    icon: "💬",
    description: "Send messages, monitor channels, and trigger agent workflows from Slack commands.",
    status: "disconnected",
  },
  {
    id: "webhooks",
    name: "HTTP / Webhooks",
    icon: "🔗",
    description: "Connect to any REST API or receive webhooks. The universal integration bridge.",
    status: "disconnected",
  },
  {
    id: "notion",
    name: "Notion",
    icon: "📝",
    description: "Sync pages, databases, and knowledge bases for agent context enrichment.",
    status: "disconnected",
  },
  {
    id: "github",
    name: "GitHub",
    icon: "🐙",
    description: "Monitor repos, create issues, review PRs, and automate developer workflows.",
    status: "connected",
    lastSync: "5 min ago",
    usageCount: 156,
  },
  {
    id: "calendar",
    name: "Google Calendar",
    icon: "📅",
    description: "Schedule meetings, check availability, and manage calendar events autonomously.",
    status: "disconnected",
  },
  {
    id: "drive",
    name: "Google Drive",
    icon: "📁",
    description: "Access, organize, and search files across your Google Drive.",
    status: "disconnected",
  },
];

type Tab = "all" | "connected" | "available";

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>(ALL_INTEGRATIONS);
  const [activeTab, setActiveTab] = useState<Tab>("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let list = integrations;
    if (activeTab === "connected") list = list.filter((i) => i.status === "connected");
    if (activeTab === "available") list = list.filter((i) => i.status !== "connected");
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((i) => i.name.toLowerCase().includes(q) || i.description.toLowerCase().includes(q));
    }
    return list;
  }, [integrations, activeTab, search]);

  const connectedCount = integrations.filter((i) => i.status === "connected").length;

  const handleConnect = (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, status: "connected" as const, lastSync: "Just now", usageCount: 0 } : i
      )
    );
  };

  const handleDisconnect = (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, status: "disconnected" as const, lastSync: undefined, usageCount: undefined } : i
      )
    );
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "all", label: "All" },
    { id: "connected", label: `Connected (${connectedCount})` },
    { id: "available", label: "Available" },
  ];

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">🧩 Forge</h1>
        <p className="text-gnosis-muted mt-1">Connect external services to supercharge your agents</p>
      </div>

      {/* Tabs + Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex gap-1 p-1 rounded-xl bg-gnosis-bg border border-gnosis-border">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.id ? "text-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
              }`}
            >
              {activeTab === tab.id && (
                <motion.div
                  layoutId="tab-bg"
                  className="absolute inset-0 bg-gnosis-primary/10 rounded-lg"
                  transition={{ duration: 0.2 }}
                />
              )}
              <span className="relative z-10">{tab.label}</span>
            </button>
          ))}
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search integrations…"
          className="flex-1 sm:max-w-xs bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50"
        />
      </div>

      {/* Grid */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab + search}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
        >
          {filtered.map((integration) => (
            <IntegrationCard
              key={integration.id}
              integration={integration}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
            />
          ))}
        </motion.div>
      </AnimatePresence>

      {filtered.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gnosis-muted text-sm">No integrations found</p>
        </div>
      )}
    </div>
  );
}
