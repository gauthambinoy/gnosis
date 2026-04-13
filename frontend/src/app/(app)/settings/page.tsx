"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import Link from "next/link";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/shared/Button";
import { Badge } from "@/components/shared/Badge";

/* ─── Providers ─── */
const PROVIDERS = [
  { id: "openrouter", name: "OpenRouter", logo: "🌐", placeholder: "sk-or-..." },
  { id: "anthropic", name: "Anthropic", logo: "🅰", placeholder: "sk-ant-..." },
  { id: "openai", name: "OpenAI", logo: "🤖", placeholder: "sk-..." },
  { id: "google", name: "Google", logo: "🔷", placeholder: "AIza..." },
  { id: "groq", name: "Groq", logo: "⚡", placeholder: "gsk_..." },
  { id: "ollama", name: "Ollama", logo: "🦙", placeholder: "http://localhost:11434" },
  { id: "together", name: "Together", logo: "🤝", placeholder: "tok_..." },
  { id: "custom", name: "Custom", logo: "🔧", placeholder: "https://..." },
] as const;

/* ─── Presets ─── */
const PRESETS = [
  { id: "budget", name: "Budget", emoji: "🟢", cost: "~$3/mo", desc: "Gemini Flash + Haiku for everything" },
  { id: "balanced", name: "Balanced", emoji: "🔵", cost: "~$12/mo", desc: "Sonnet for reasoning, Haiku for classify" },
  { id: "performance", name: "Performance", emoji: "🟣", cost: "~$45/mo", desc: "Opus for deep, Sonnet for standard" },
  { id: "local", name: "Local", emoji: "⚪", cost: "$0", desc: "Ollama models, 100% private" },
  { id: "speed", name: "Speed", emoji: "⚡", cost: "~$8/mo", desc: "Groq for ultra-low latency" },
];

/* ─── Tier models ─── */
const TIERS = [
  { id: "l0", label: "L0 Reflex", desc: "Instant pattern-match" },
  { id: "l1", label: "L1 Classify", desc: "Intent routing" },
  { id: "l2", label: "L2 Standard", desc: "General reasoning" },
  { id: "l3", label: "L3 Deep", desc: "Complex analysis" },
] as const;

const MODEL_OPTIONS = [
  "Auto (preset default)",
  "claude-3.5-sonnet",
  "claude-3-haiku",
  "claude-3-opus",
  "gpt-4o",
  "gpt-4o-mini",
  "gemini-1.5-flash",
  "gemini-1.5-pro",
  "llama-3.1-70b",
  "llama-3.1-8b",
  "mixtral-8x7b",
  "qwen-2.5-72b",
];

/* ─── Integration quick-view data ─── */
const QUICK_INTEGRATIONS = [
  { id: "gmail", name: "Gmail", icon: "📧", connected: true },
  { id: "sheets", name: "Sheets", icon: "📊", connected: true },
  { id: "slack", name: "Slack", icon: "💬", connected: false },
  { id: "webhooks", name: "Webhooks", icon: "🔗", connected: false },
  { id: "github", name: "GitHub", icon: "🐙", connected: true },
  { id: "calendar", name: "Calendar", icon: "📅", connected: false },
];

export default function SettingsPage() {
  const [provider, setProvider] = useState("openrouter");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [activePreset, setActivePreset] = useState("balanced");
  const [tierOverrides, setTierOverrides] = useState<Record<string, string>>({
    l0: "Auto (preset default)",
    l1: "Auto (preset default)",
    l2: "Auto (preset default)",
    l3: "Auto (preset default)",
  });
  const [budget, setBudget] = useState(25);
  const [spent] = useState(8.42);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"idle" | "success" | "error">("idle");
  const [providerOpen, setProviderOpen] = useState(false);

  const currentProvider = PROVIDERS.find((p) => p.id === provider)!;

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult("idle");
    await new Promise((r) => setTimeout(r, 1500));
    setTestResult(apiKey.length > 4 ? "success" : "error");
    setTesting(false);
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">⚙ Settings</h1>
        <p className="text-gnosis-muted mt-1">Configure your Gnosis experience</p>
      </div>

      {/* ─── LLM Configuration ─── */}
      <Card>
        <h2 className="text-lg font-semibold text-gnosis-text mb-6">LLM Configuration</h2>

        {/* Provider selector */}
        <div className="mb-6">
          <label className="text-sm text-gnosis-muted mb-2 block">Provider</label>
          <div className="relative">
            <button
              onClick={() => setProviderOpen(!providerOpen)}
              className="w-full flex items-center justify-between bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text hover:border-gnosis-primary/30 transition-colors"
            >
              <span className="flex items-center gap-2">
                <span>{currentProvider.logo}</span>
                <span>{currentProvider.name}</span>
              </span>
              <span className="text-gnosis-muted">{providerOpen ? "▲" : "▼"}</span>
            </button>
            {providerOpen && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute z-20 mt-1 w-full bg-gnosis-surface border border-gnosis-border rounded-xl overflow-hidden shadow-2xl"
              >
                {PROVIDERS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => { setProvider(p.id); setProviderOpen(false); }}
                    className={clsx(
                      "w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors",
                      provider === p.id
                        ? "bg-gnosis-primary/10 text-gnosis-primary"
                        : "text-gnosis-text hover:bg-white/[0.03]"
                    )}
                  >
                    <span>{p.logo}</span>
                    <span>{p.name}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </div>
        </div>

        {/* API Key */}
        <div className="mb-6">
          <label className="text-sm text-gnosis-muted mb-2 block">API Key</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => { setApiKey(e.target.value); setTestResult("idle"); }}
                placeholder={currentProvider.placeholder}
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gnosis-muted hover:text-gnosis-text text-xs transition-colors"
              >
                {showKey ? "Hide" : "Show"}
              </button>
            </div>
            <Button
              variant="secondary"
              size="md"
              onClick={handleTestConnection}
              disabled={testing || !apiKey}
            >
              {testing ? (
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="inline-block w-4 h-4 border-2 border-gnosis-primary border-t-transparent rounded-full"
                />
              ) : (
                "Test"
              )}
            </Button>
          </div>
          {testResult === "success" && (
            <p className="text-xs text-gnosis-success mt-1.5">✓ Connection successful</p>
          )}
          {testResult === "error" && (
            <p className="text-xs text-gnosis-error mt-1.5">✗ Connection failed — check your key</p>
          )}
        </div>

        {/* Presets */}
        <div className="mb-6">
          <label className="text-sm text-gnosis-muted mb-3 block">Model Preset</label>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => setActivePreset(preset.id)}
                className={clsx(
                  "flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-left",
                  activePreset === preset.id
                    ? "border-gnosis-primary bg-gnosis-primary/5"
                    : "border-gnosis-border hover:border-gnosis-border/80"
                )}
              >
                <span>{preset.emoji}</span>
                <div>
                  <span className={clsx("text-sm font-medium", activePreset === preset.id ? "text-gnosis-primary" : "text-gnosis-text")}>
                    {preset.name}
                  </span>
                  <p className="text-xs text-gnosis-muted">{preset.cost}</p>
                </div>
              </button>
            ))}
          </div>
          <p className="text-xs text-gnosis-muted mt-2">
            {PRESETS.find((p) => p.id === activePreset)?.desc}
          </p>
        </div>

        {/* Per-tier overrides */}
        <div className="mb-6">
          <label className="text-sm text-gnosis-muted mb-3 block">Per-Tier Model Override</label>
          <div className="space-y-3">
            {TIERS.map((tier) => (
              <div key={tier.id} className="flex items-center gap-4">
                <div className="w-28 shrink-0">
                  <p className="text-sm font-medium text-gnosis-text">{tier.label}</p>
                  <p className="text-[11px] text-gnosis-muted">{tier.desc}</p>
                </div>
                <select
                  value={tierOverrides[tier.id]}
                  onChange={(e) => setTierOverrides((prev) => ({ ...prev, [tier.id]: e.target.value }))}
                  className="flex-1 bg-gnosis-bg border border-gnosis-border rounded-xl px-3 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50 appearance-none cursor-pointer"
                >
                  {MODEL_OPTIONS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        {/* Cost limit */}
        <div>
          <label className="text-sm text-gnosis-muted mb-2 block">Monthly Budget</label>
          <div className="flex items-center gap-4 mb-2">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gnosis-muted">$</span>
              <input
                type="number"
                min={0}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-28 bg-gnosis-bg border border-gnosis-border rounded-xl pl-7 pr-3 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50"
              />
            </div>
            <span className="text-xs text-gnosis-muted">
              ${spent.toFixed(2)} spent of ${budget} this month
            </span>
          </div>
          <div className="w-full h-2 bg-gnosis-bg rounded-full overflow-hidden border border-gnosis-border">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((spent / budget) * 100, 100)}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className={clsx(
                "h-full rounded-full",
                spent / budget > 0.9 ? "bg-gnosis-error" : spent / budget > 0.7 ? "bg-yellow-400" : "bg-gnosis-primary"
              )}
            />
          </div>
        </div>
      </Card>

      {/* ─── Profile ─── */}
      <Card>
        <h2 className="text-lg font-semibold text-gnosis-text mb-6">Profile</h2>
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-gnosis-primary/20 flex items-center justify-center text-gnosis-primary text-xl font-bold">
            G
          </div>
          <div className="flex-1 space-y-3">
            <div>
              <label className="text-xs text-gnosis-muted mb-1 block">Name</label>
              <input
                type="text"
                defaultValue="Gautham"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50"
              />
            </div>
            <div>
              <label className="text-xs text-gnosis-muted mb-1 block">Email</label>
              <input
                type="email"
                defaultValue="gautham@gnosis.dev"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50"
              />
            </div>
          </div>
        </div>

        <div>
          <label className="text-xs text-gnosis-muted mb-2 block">Theme</label>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gnosis-primary bg-gnosis-primary/5 text-sm text-gnosis-primary">
              🌙 Dark
            </button>
            <button
              disabled
              className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gnosis-border text-sm text-gnosis-muted opacity-40 cursor-not-allowed"
            >
              ☀ Light
            </button>
          </div>
        </div>
      </Card>

      {/* ─── Integrations Quick View ─── */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gnosis-text">Integrations</h2>
          <Link href="/integrations" className="text-xs text-gnosis-primary hover:underline">
            Manage all →
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {QUICK_INTEGRATIONS.map((intg) => (
            <div
              key={intg.id}
              className="flex items-center gap-3 p-3 rounded-xl border border-gnosis-border bg-gnosis-bg"
            >
              <span className="text-xl">{intg.icon}</span>
              <div className="min-w-0">
                <p className="text-sm text-gnosis-text truncate">{intg.name}</p>
              </div>
              <Badge variant={intg.connected ? "success" : "default"} className="ml-auto shrink-0">
                {intg.connected ? "On" : "Off"}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      {/* ─── Save ─── */}
      <div className="flex justify-end gap-3">
        <Button variant="secondary">Reset</Button>
        <Button>Save Settings</Button>
      </div>
    </div>
  );
}
