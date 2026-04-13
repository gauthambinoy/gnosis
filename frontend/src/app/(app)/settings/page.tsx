"use client";

import { useState } from "react";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/shared/Button";

const PRESETS = [
  { id: "budget", name: "Budget", cost: "~$3/mo", desc: "Gemini Flash + Haiku for everything" },
  { id: "balanced", name: "Balanced", cost: "~$12/mo", desc: "Sonnet for reasoning, Haiku for classify" },
  { id: "max", name: "Maximum", cost: "~$45/mo", desc: "Opus for deep, Sonnet for standard" },
  { id: "local", name: "Local Only", cost: "$0", desc: "Ollama models, 100% private" },
  { id: "speed", name: "Speed", cost: "~$8/mo", desc: "Groq for ultra-low latency" },
];

export default function SettingsPage() {
  const [activePreset, setActivePreset] = useState("balanced");
  const [openRouterKey, setOpenRouterKey] = useState("");

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">⚙ Settings</h1>
        <p className="text-gnosis-muted mt-1">Configure your Gnosis experience</p>
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-gnosis-text mb-4">LLM Configuration</h2>
        
        <div className="mb-6">
          <label className="text-sm text-gnosis-muted mb-2 block">OpenRouter API Key</label>
          <input
            type="password"
            value={openRouterKey}
            onChange={(e) => setOpenRouterKey(e.target.value)}
            placeholder="sk-or-..."
            className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50"
          />
          <p className="text-xs text-gnosis-muted mt-1">Get yours at openrouter.ai — gives access to 200+ models</p>
        </div>

        <div>
          <label className="text-sm text-gnosis-muted mb-3 block">Preset</label>
          <div className="grid grid-cols-1 gap-2">
            {PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => setActivePreset(preset.id)}
                className={
                  "flex items-center justify-between p-4 rounded-xl border transition-all text-left " +
                  (activePreset === preset.id
                    ? "border-gnosis-primary bg-gnosis-primary/5"
                    : "border-gnosis-border hover:border-gnosis-border/80")
                }
              >
                <div>
                  <span className={"font-medium " + (activePreset === preset.id ? "text-gnosis-primary" : "text-gnosis-text")}>
                    {preset.name}
                  </span>
                  <p className="text-xs text-gnosis-muted mt-0.5">{preset.desc}</p>
                </div>
                <span className="text-sm text-gnosis-muted">{preset.cost}</span>
              </button>
            ))}
          </div>
        </div>
      </Card>

      <div className="flex justify-end">
        <Button>Save Settings</Button>
      </div>
    </div>
  );
}
