"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

export interface AgentConfig {
  name: string;
  description: string;
  emoji: string;
  triggers: string[];
  integrations: string[];
}

interface AgentPreviewProps {
  config: AgentConfig;
  onAwaken: () => void;
  isAwakening?: boolean;
}

const INTEGRATION_META: Record<string, { icon: string; label: string }> = {
  gmail: { icon: "✉️", label: "Gmail" },
  slack: { icon: "💬", label: "Slack" },
  sheets: { icon: "📊", label: "Google Sheets" },
  calendar: { icon: "📅", label: "Calendar" },
  drive: { icon: "📁", label: "Google Drive" },
  github: { icon: "🐙", label: "GitHub" },
  notion: { icon: "📓", label: "Notion" },
  webhook: { icon: "🔗", label: "Webhook" },
};

function getIntegrationMeta(key: string) {
  const normalized = key.toLowerCase().replace(/[^a-z]/g, "");
  return (
    INTEGRATION_META[normalized] ?? {
      icon: "⚡",
      label: key.charAt(0).toUpperCase() + key.slice(1),
    }
  );
}

export function AgentPreview({
  config,
  onAwaken,
  isAwakening = false,
}: AgentPreviewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="w-full max-w-lg mx-auto my-6"
    >
      <div className="rounded-2xl border border-gnosis-gold/30 bg-gnosis-surface overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-gnosis-border">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gnosis-bg border border-gnosis-gold/20 flex items-center justify-center text-2xl">
              {config.emoji || "✦"}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-display text-xl font-semibold text-gnosis-text truncate">
                {config.name}
              </h3>
              <p className="text-xs text-gnosis-muted mt-0.5 line-clamp-2">
                {config.description}
              </p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {/* Triggers */}
          {config.triggers.length > 0 && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gnosis-muted font-medium">
                Triggers
              </span>
              <div className="flex flex-wrap gap-2 mt-2">
                {config.triggers.map((trigger) => (
                  <span
                    key={trigger}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-gnosis-bg border border-gnosis-border text-xs text-gnosis-text"
                  >
                    <span className="text-gnosis-primary">⚡</span>
                    {trigger}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Integrations */}
          {config.integrations.length > 0 && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gnosis-muted font-medium">
                Integrations
              </span>
              <div className="flex flex-wrap gap-2 mt-2">
                {config.integrations.map((integration) => {
                  const meta = getIntegrationMeta(integration);
                  return (
                    <span
                      key={integration}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gnosis-bg border border-gnosis-border text-xs text-gnosis-text"
                    >
                      <span>{meta.icon}</span>
                      {meta.label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer with Awaken button */}
        <div className="px-6 pb-6 pt-2">
          <button
            onClick={onAwaken}
            disabled={isAwakening}
            className={clsx(
              "w-full py-3 rounded-xl font-medium text-sm transition-all duration-300",
              "bg-gnosis-primary text-gnosis-bg",
              "hover:shadow-[0_0_40px_rgba(200,255,0,0.3)]",
              "active:scale-[0.98]",
              "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none",
              isAwakening && "animate-pulse-glow"
            )}
          >
            {isAwakening ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-gnosis-bg/30 border-t-gnosis-bg rounded-full animate-spin" />
                Awakening…
              </span>
            ) : (
              "✦ Awaken Agent"
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
