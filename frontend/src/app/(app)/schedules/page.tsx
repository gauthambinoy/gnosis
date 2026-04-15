"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────
interface Schedule {
  id: string;
  agent_id: string;
  name: string;
  cron_expression: string;
  status: "active" | "paused" | "completed" | "error";
  input_data: Record<string, unknown>;
  max_runs: number | null;
  run_count: number;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
  error_count: number;
  last_error: string | null;
}

interface Stats {
  total: number;
  by_status: Record<string, number>;
}

const PRESETS = [
  { label: "Every 5 min", value: "every:5m" },
  { label: "Hourly", value: "hourly" },
  { label: "Daily at 9 AM", value: "daily:09:00" },
  { label: "Weekly Monday", value: "weekly" },
];

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/20 text-green-400 border-green-500/30",
  paused: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  completed: "bg-white/10 text-white/50 border-white/10",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [stats, setStats] = useState<Stats>({ total: 0, by_status: {} });
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  // Form state
  const [form, setForm] = useState({
    agent_id: "",
    name: "",
    cron_expression: "",
    max_runs: "",
  });

  const fetchSchedules = useCallback(async () => {
    try {
      const [listRes, statsRes] = await Promise.all([
        api.get("/schedules"),
        api.get("/schedules/stats/overview"),
      ]);
      if (listRes.ok) {
        const data = await listRes.json();
        setSchedules(data.schedules);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch {
      /* network error — keep stale data */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedules();
    const iv = setInterval(fetchSchedules, 15_000);
    return () => clearInterval(iv);
  }, [fetchSchedules]);

  async function handleCreate() {
    const body: Record<string, unknown> = {
      agent_id: form.agent_id,
      name: form.name,
      cron_expression: form.cron_expression,
      input_data: {},
    };
    if (form.max_runs) body.max_runs = Number(form.max_runs);

    const res = await api.post("/schedules", body);
    if (res.ok) {
      setShowCreate(false);
      setForm({ agent_id: "", name: "", cron_expression: "", max_runs: "" });
      fetchSchedules();
    }
  }

  async function handleAction(id: string, action: "pause" | "resume" | "delete") {
    if (action === "delete") {
      await api.delete(`/schedules/${id}`);
    } else {
      await api.post(`/schedules/${id}/${action}`);
    }
    fetchSchedules();
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Schedules</h1>
          <p className="text-white/40 mt-1 text-sm">
            Automate agent execution with cron-based scheduling
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-5 py-2.5 rounded-xl bg-[#C8FF00] text-black font-semibold text-sm hover:brightness-110 transition"
        >
          + New Schedule
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total", value: stats.total, color: "text-white" },
          { label: "Active", value: stats.by_status?.active ?? 0, color: "text-green-400" },
          { label: "Paused", value: stats.by_status?.paused ?? 0, color: "text-yellow-400" },
          { label: "Errors", value: stats.by_status?.error ?? 0, color: "text-red-400" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-white/5 bg-[#0A0A0A] p-4"
          >
            <p className="text-xs text-white/40 uppercase tracking-wider">{s.label}</p>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Schedule list */}
      {loading ? (
        <div className="text-white/30 text-center py-20 text-sm">Loading schedules…</div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-20 border border-white/5 rounded-2xl bg-[#0A0A0A]">
          <p className="text-white/30 text-lg">No schedules yet</p>
          <p className="text-white/20 text-sm mt-1">
            Create one to automate your agents
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((s) => (
            <motion.div
              key={s.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl border border-white/5 bg-[#0A0A0A] p-5 flex flex-col md:flex-row md:items-center gap-4"
            >
              {/* Info */}
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-white truncate">{s.name}</span>
                  <span
                    className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full border ${STATUS_COLORS[s.status]}`}
                  >
                    {s.status}
                  </span>
                </div>
                <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-white/30">
                  <span>Agent: {s.agent_id}</span>
                  <span>Cron: {s.cron_expression}</span>
                  <span>Runs: {s.run_count}{s.max_runs ? ` / ${s.max_runs}` : ""}</span>
                </div>
              </div>

              {/* Times */}
              <div className="flex gap-6 text-xs text-white/40 shrink-0">
                <div>
                  <p className="uppercase tracking-wider text-[10px] text-white/20">Last run</p>
                  <p>{formatDate(s.last_run)}</p>
                </div>
                <div>
                  <p className="uppercase tracking-wider text-[10px] text-white/20">Next run</p>
                  <p>{formatDate(s.next_run)}</p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 shrink-0">
                {s.status === "active" && (
                  <button
                    onClick={() => handleAction(s.id, "pause")}
                    className="px-3 py-1.5 rounded-lg text-xs border border-white/10 text-white/60 hover:bg-white/5 transition"
                  >
                    Pause
                  </button>
                )}
                {s.status === "paused" && (
                  <button
                    onClick={() => handleAction(s.id, "resume")}
                    className="px-3 py-1.5 rounded-lg text-xs border border-[#C8FF00]/30 text-[#C8FF00] hover:bg-[#C8FF00]/10 transition"
                  >
                    Resume
                  </button>
                )}
                <button
                  onClick={() => handleAction(s.id, "delete")}
                  className="px-3 py-1.5 rounded-lg text-xs border border-red-500/20 text-red-400 hover:bg-red-500/10 transition"
                >
                  Delete
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Create modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setShowCreate(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 shadow-2xl space-y-5"
            >
              <h2 className="text-xl font-bold text-white">Create Schedule</h2>

              {/* Name */}
              <div>
                <label className="block text-xs text-white/40 mb-1">Name</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/20 outline-none focus:border-[#C8FF00]/40"
                  placeholder="Daily report run"
                />
              </div>

              {/* Agent ID */}
              <div>
                <label className="block text-xs text-white/40 mb-1">Agent ID</label>
                <input
                  value={form.agent_id}
                  onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/20 outline-none focus:border-[#C8FF00]/40"
                  placeholder="agent-uuid"
                />
              </div>

              {/* Cron expression */}
              <div>
                <label className="block text-xs text-white/40 mb-1">Cron Expression</label>
                <input
                  value={form.cron_expression}
                  onChange={(e) => setForm({ ...form, cron_expression: e.target.value })}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/20 outline-none focus:border-[#C8FF00]/40"
                  placeholder="every:5m"
                />
                <div className="flex gap-2 mt-2 flex-wrap">
                  {PRESETS.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setForm({ ...form, cron_expression: p.value })}
                      className={`px-3 py-1 rounded-lg text-xs border transition ${
                        form.cron_expression === p.value
                          ? "border-[#C8FF00]/50 bg-[#C8FF00]/10 text-[#C8FF00]"
                          : "border-white/10 text-white/40 hover:bg-white/5"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Max runs */}
              <div>
                <label className="block text-xs text-white/40 mb-1">
                  Max Runs <span className="text-white/20">(optional)</span>
                </label>
                <input
                  type="number"
                  min={1}
                  value={form.max_runs}
                  onChange={(e) => setForm({ ...form, max_runs: e.target.value })}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/20 outline-none focus:border-[#C8FF00]/40"
                  placeholder="Unlimited"
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 rounded-xl text-sm text-white/40 hover:text-white/60 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={!form.name || !form.agent_id || !form.cron_expression}
                  className="px-5 py-2 rounded-xl bg-[#C8FF00] text-black font-semibold text-sm hover:brightness-110 transition disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Create
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
