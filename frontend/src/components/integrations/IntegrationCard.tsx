"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { Badge } from "@/components/shared/Badge";

export interface Integration {
  id: string;
  name: string;
  icon: string;
  description: string;
  status: "connected" | "disconnected" | "error";
  lastSync?: string;
  usageCount?: number;
}

interface IntegrationCardProps {
  integration: Integration;
  onConnect: (id: string) => void;
  onDisconnect: (id: string) => void;
}

export function IntegrationCard({ integration, onConnect, onDisconnect }: IntegrationCardProps) {
  const [loading, setLoading] = useState(false);

  const handleAction = async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1200));
    if (integration.status === "connected") {
      onDisconnect(integration.id);
    } else {
      onConnect(integration.id);
    }
    setLoading(false);
  };

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.2 }}
      className="rounded-2xl border border-gnosis-border bg-gnosis-surface p-5 flex flex-col gap-4 transition-colors hover:border-gnosis-primary/20"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{integration.icon}</span>
          <div>
            <h3 className="text-sm font-semibold text-gnosis-text">{integration.name}</h3>
            <p className="text-xs text-gnosis-muted mt-0.5 leading-relaxed">{integration.description}</p>
          </div>
        </div>
        <Badge
          variant={
            integration.status === "connected"
              ? "success"
              : integration.status === "error"
                ? "error"
                : "default"
          }
        >
          {integration.status === "connected" ? "Connected" : integration.status === "error" ? "Error" : "Inactive"}
        </Badge>
      </div>

      {integration.status === "connected" && (
        <div className="flex items-center gap-4 text-xs text-gnosis-muted border-t border-gnosis-border pt-3">
          {integration.lastSync && (
            <span>Last sync: {integration.lastSync}</span>
          )}
          {integration.usageCount !== undefined && (
            <span>{integration.usageCount} actions</span>
          )}
        </div>
      )}

      <button
        onClick={handleAction}
        disabled={loading}
        className={clsx(
          "w-full rounded-xl py-2 text-sm font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed",
          integration.status === "connected"
            ? "border border-gnosis-border text-gnosis-muted hover:border-gnosis-error/50 hover:text-gnosis-error"
            : "bg-gnosis-primary text-gnosis-bg hover:shadow-[0_0_30px_rgba(200,255,0,0.3)]"
        )}
      >
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full"
            />
            {integration.status === "connected" ? "Disconnecting…" : "Connecting…"}
          </span>
        ) : integration.status === "connected" ? (
          "Disconnect"
        ) : (
          "Connect"
        )}
      </button>
    </motion.div>
  );
}
