"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/shared/Card";
import { api } from "@/lib/api";

interface InsightItem {
  id: string;
  type: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
  suggested_action: string;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  info: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" },
  warning: { bg: "bg-yellow-500/10", text: "text-yellow-400", border: "border-yellow-500/20" },
  critical: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20" },
};

export default function OraclePage() {
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchInsights() {
      try {
        const res = await api.get("/oracle/insights");
        if (res.ok) {
          const data = await res.json();
          setInsights(data.insights || []);
        }
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    }
    fetchInsights();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">⟐ The Oracle</h1>
        <p className="text-gnosis-muted mt-1">Proactive insights across your agent network</p>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
          ))}
        </div>
      ) : insights.length === 0 ? (
        <Card className="text-center py-16">
          <p className="text-4xl mb-4">⟐</p>
          <h3 className="text-xl font-display font-bold text-gnosis-text mb-2">The Oracle is listening</h3>
          <p className="text-gnosis-muted">Insights will appear here as your agents accumulate data and the Oracle detects patterns.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {insights.map((insight, i) => {
            const style = SEVERITY_STYLES[insight.severity];
            return (
              <motion.div
                key={insight.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className={style.border + " border"}>
                  <div className="flex items-start gap-4">
                    <div className={style.bg + " " + style.text + " px-2 py-1 rounded-lg text-xs font-medium uppercase"}>
                      {insight.severity}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gnosis-text">{insight.title}</h3>
                      <p className="text-sm text-gnosis-muted mt-1">{insight.description}</p>
                      {insight.suggested_action && (
                        <p className="text-sm text-gnosis-primary mt-2">→ {insight.suggested_action}</p>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
