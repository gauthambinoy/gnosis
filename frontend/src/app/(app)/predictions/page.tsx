"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Prediction {
  id: string;
  suggested_agent: string;
  confidence: number;
  reasoning: string;
  pattern_source: string;
  status: string;
  created_at: string;
}

interface Pattern {
  id: string;
  action_sequence: string[];
  frequency: number;
  confidence: number;
  time_of_day: string;
  day_of_week: string[];
  last_seen: string;
}

interface Stats {
  total_actions_tracked: number;
  patterns_detected: number;
  total_predictions: number;
  accepted: number;
  dismissed: number;
  templates_available: number;
  accuracy_estimate: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"predictions" | "patterns" | "stats">("predictions");

  const fetchAll = useCallback(async () => {
    try {
      const [predRes, patRes, statRes] = await Promise.all([
        api.get("/predictions"),
        api.get("/predictions/patterns"),
        api.get("/predictions/stats"),
      ]);
      const predData = await predRes.json();
      const patData = await patRes.json();
      const statData = await statRes.json();
      setPredictions(predData.predictions || []);
      setPatterns(patData.patterns || []);
      setStats(statData);
    } catch {
      // API may not be available — show empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleAccept = async (id: string) => {
    try {
      await api.post(`/predictions/accept/${id}`);
      setPredictions((prev) => prev.map((p) => (p.id === id ? { ...p, status: "accepted" } : p)));
    } catch { /* ignore */ }
  };

  const handleDismiss = async (id: string) => {
    try {
      await api.post(`/predictions/dismiss/${id}`);
      setPredictions((prev) => prev.map((p) => (p.id === id ? { ...p, status: "dismissed" } : p)));
    } catch { /* ignore */ }
  };

  const confidenceColor = (c: number) => {
    if (c >= 0.85) return "text-green-400";
    if (c >= 0.7) return "text-yellow-400";
    return "text-orange-400";
  };

  const confidenceBg = (c: number) => {
    if (c >= 0.85) return "bg-green-500/20 border-green-500/30";
    if (c >= 0.7) return "bg-yellow-500/20 border-yellow-500/30";
    return "bg-orange-500/20 border-orange-500/30";
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="text-3xl font-bold text-gnosis-text flex items-center gap-3">
          <span className="text-4xl">🔮</span> Predictions
        </h1>
        <p className="text-gnosis-muted mt-2">Gnosis knows what you need before you do</p>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gnosis-border pb-2">
        {(["predictions", "patterns", "stats"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
              tab === t
                ? "bg-gnosis-primary/10 text-gnosis-primary border-b-2 border-gnosis-primary"
                : "text-gnosis-muted hover:text-gnosis-text"
            }`}
          >
            {t === "predictions" && "🎯 Predictions"}
            {t === "patterns" && "📊 Patterns"}
            {t === "stats" && "📈 Stats"}
          </button>
        ))}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-20">
            <div className="text-4xl mb-4 animate-pulse">🔮</div>
            <p className="text-gnosis-muted">Analysing patterns...</p>
          </motion.div>
        ) : (
          <>
            {/* Predictions Tab */}
            {tab === "predictions" && (
              <motion.div key="predictions" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {predictions.length === 0 ? (
                  <div className="col-span-full text-center py-16 text-gnosis-muted">
                    <div className="text-5xl mb-4">🔮</div>
                    <p className="text-lg">No predictions yet</p>
                    <p className="text-sm mt-1">Use Gnosis more and patterns will emerge</p>
                  </div>
                ) : (
                  predictions.map((pred, i) => (
                    <motion.div
                      key={pred.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className={`rounded-xl border p-5 space-y-3 ${
                        pred.status === "accepted"
                          ? "border-green-500/30 bg-green-500/5"
                          : pred.status === "dismissed"
                          ? "border-gnosis-border/50 bg-gnosis-surface/50 opacity-60"
                          : "border-gnosis-border bg-gnosis-surface"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <h3 className="font-semibold text-gnosis-text text-sm">{pred.suggested_agent}</h3>
                        <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${confidenceBg(pred.confidence)} ${confidenceColor(pred.confidence)}`}>
                          {Math.round(pred.confidence * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-gnosis-muted">{pred.reasoning}</p>
                      <div className="text-[10px] text-gnosis-muted/60 font-mono">
                        src: {pred.pattern_source}
                      </div>
                      {/* Confidence bar */}
                      <div className="h-1 rounded-full bg-gnosis-border overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pred.confidence * 100}%` }}
                          transition={{ delay: i * 0.05 + 0.3, duration: 0.6 }}
                          className={`h-full rounded-full ${pred.confidence >= 0.85 ? "bg-green-500" : pred.confidence >= 0.7 ? "bg-yellow-500" : "bg-orange-500"}`}
                        />
                      </div>
                      {pred.status === "pending" && (
                        <div className="flex gap-2 pt-1">
                          <button onClick={() => handleAccept(pred.id)} className="flex-1 px-3 py-1.5 rounded-lg bg-gnosis-primary/20 text-gnosis-primary text-xs font-medium hover:bg-gnosis-primary/30 transition-colors">
                            ✓ Accept
                          </button>
                          <button onClick={() => handleDismiss(pred.id)} className="flex-1 px-3 py-1.5 rounded-lg bg-white/5 text-gnosis-muted text-xs font-medium hover:bg-white/10 transition-colors">
                            ✕ Dismiss
                          </button>
                        </div>
                      )}
                      {pred.status === "accepted" && (
                        <div className="text-xs text-green-400 font-medium">✓ Agent deployed</div>
                      )}
                      {pred.status === "dismissed" && (
                        <div className="text-xs text-gnosis-muted">Dismissed</div>
                      )}
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}

            {/* Patterns Tab */}
            {tab === "patterns" && (
              <motion.div key="patterns" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="space-y-4">
                {patterns.length === 0 ? (
                  <div className="text-center py-16 text-gnosis-muted">
                    <div className="text-5xl mb-4">📊</div>
                    <p className="text-lg">No patterns detected yet</p>
                    <p className="text-sm mt-1">Patterns emerge after repeated usage</p>
                  </div>
                ) : (
                  patterns.map((pat, i) => (
                    <motion.div
                      key={pat.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.08 }}
                      className="rounded-xl border border-gnosis-border bg-gnosis-surface p-5"
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <div className="flex gap-1">
                          {pat.action_sequence.map((a, j) => (
                            <span key={j}>
                              <span className="px-2 py-0.5 rounded bg-gnosis-primary/10 text-gnosis-primary text-xs font-mono">{a}</span>
                              {j < pat.action_sequence.length - 1 && <span className="text-gnosis-muted mx-1">→</span>}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex gap-4 text-xs text-gnosis-muted">
                        <span>Frequency: <strong className="text-gnosis-text">{pat.frequency}×</strong></span>
                        <span>Confidence: <strong className={confidenceColor(pat.confidence)}>{Math.round(pat.confidence * 100)}%</strong></span>
                        <span>Time: {pat.time_of_day}</span>
                        <span>Days: {pat.day_of_week.join(", ")}</span>
                      </div>
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}

            {/* Stats Tab */}
            {tab === "stats" && (
              <motion.div key="stats" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {stats ? (
                  <>
                    {[
                      { label: "Actions Tracked", value: stats.total_actions_tracked, icon: "📝" },
                      { label: "Patterns Found", value: stats.patterns_detected, icon: "🧩" },
                      { label: "Predictions Made", value: stats.total_predictions, icon: "🔮" },
                      { label: "Accepted", value: stats.accepted, icon: "✅" },
                      { label: "Dismissed", value: stats.dismissed, icon: "❌" },
                      { label: "Templates", value: stats.templates_available, icon: "📋" },
                      { label: "Accuracy", value: `${Math.round(stats.accuracy_estimate * 100)}%`, icon: "🎯" },
                    ].map((s, i) => (
                      <motion.div
                        key={s.label}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.06 }}
                        className="rounded-xl border border-gnosis-border bg-gnosis-surface p-5 text-center"
                      >
                        <div className="text-2xl mb-2">{s.icon}</div>
                        <div className="text-2xl font-bold text-gnosis-text">{s.value}</div>
                        <div className="text-xs text-gnosis-muted mt-1">{s.label}</div>
                      </motion.div>
                    ))}
                  </>
                ) : (
                  <div className="col-span-full text-center py-16 text-gnosis-muted">
                    No stats available
                  </div>
                )}
              </motion.div>
            )}
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
