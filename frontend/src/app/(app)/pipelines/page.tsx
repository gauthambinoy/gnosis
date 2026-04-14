"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence, Reorder } from "framer-motion";

// ── Types ───────────────────────────────────────────────────────
interface PipelineStep {
  id: string;
  agent_id: string;
  name: string;
  order: number;
  transform_input?: string | null;
  condition?: string | null;
  timeout_seconds: number;
  max_retries: number;
}

interface Pipeline {
  id: string;
  name: string;
  description: string;
  steps: PipelineStep[];
  status: string;
  created_at: string;
  updated_at: string;
}

interface StepResult {
  step_id: string;
  status: string;
  output: Record<string, unknown>;
  error?: string | null;
  duration_ms: number;
  started_at?: string | null;
  completed_at?: string | null;
}

interface PipelineRun {
  id: string;
  pipeline_id: string;
  status: string;
  initial_input: Record<string, unknown>;
  step_results: StepResult[];
  current_step: number;
  started_at: string;
  completed_at?: string | null;
  total_duration_ms: number;
}

interface PipelineStats {
  total_pipelines: number;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
}

// ── API helpers ─────────────────────────────────────────────────
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── Status badge ────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-white/10 text-white/60",
    active: "bg-[#C8FF00]/15 text-[#C8FF00]",
    running: "bg-blue-500/15 text-blue-400",
    completed: "bg-emerald-500/15 text-emerald-400",
    failed: "bg-red-500/15 text-red-400",
    paused: "bg-amber-500/15 text-amber-400",
    pending: "bg-white/10 text-white/40",
    skipped: "bg-white/5 text-white/30",
  };
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status] || colors.draft}`}>
      {status}
    </span>
  );
}

// ── Step result indicator ───────────────────────────────────────
function StepResultDot({ status }: { status: string }) {
  const color =
    status === "completed" ? "bg-emerald-400" :
    status === "failed" ? "bg-red-400" :
    status === "skipped" ? "bg-white/20" :
    status === "running" ? "bg-blue-400 animate-pulse" :
    "bg-white/10";
  return <div className={`w-3 h-3 rounded-full ${color}`} title={status} />;
}

// ── Main Page ───────────────────────────────────────────────────
export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showExecute, setShowExecute] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newSteps, setNewSteps] = useState<{ agent_id: string; name: string }[]>([]);

  // Execute form
  const [executeInput, setExecuteInput] = useState("{}");
  const [executeResult, setExecuteResult] = useState<PipelineRun | null>(null);
  const [executing, setExecuting] = useState(false);

  // Add step form
  const [addStepAgentId, setAddStepAgentId] = useState("");
  const [addStepName, setAddStepName] = useState("");

  const fetchPipelines = useCallback(async () => {
    try {
      setLoading(true);
      const [pData, sData] = await Promise.all([
        api<{ pipelines: Pipeline[] }>("/api/v1/pipelines"),
        api<PipelineStats>("/api/v1/pipelines/stats"),
      ]);
      setPipelines(pData.pipelines);
      setStats(sData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load pipelines");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPipelines(); }, [fetchPipelines]);

  const selectPipeline = async (p: Pipeline) => {
    setSelectedPipeline(p);
    setExecuteResult(null);
    try {
      const data = await api<{ runs: PipelineRun[] }>(`/api/v1/pipelines/${p.id}/runs`);
      setRuns(data.runs);
    } catch {
      setRuns([]);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const pipeline = await api<Pipeline>("/api/v1/pipelines", {
        method: "POST",
        body: JSON.stringify({ name: newName, description: newDesc, steps: newSteps }),
      });
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
      setNewSteps([]);
      await fetchPipelines();
      setSelectedPipeline(pipeline);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create pipeline");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api(`/api/v1/pipelines/${id}`, { method: "DELETE" });
      if (selectedPipeline?.id === id) setSelectedPipeline(null);
      await fetchPipelines();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete pipeline");
    }
  };

  const handleAddStep = async () => {
    if (!selectedPipeline || !addStepAgentId.trim()) return;
    try {
      await api(`/api/v1/pipelines/${selectedPipeline.id}/steps`, {
        method: "POST",
        body: JSON.stringify({ agent_id: addStepAgentId, name: addStepName || "New Step" }),
      });
      const updated = await api<Pipeline>(`/api/v1/pipelines/${selectedPipeline.id}`);
      setSelectedPipeline(updated);
      setAddStepAgentId("");
      setAddStepName("");
      await fetchPipelines();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add step");
    }
  };

  const handleRemoveStep = async (stepId: string) => {
    if (!selectedPipeline) return;
    try {
      await api(`/api/v1/pipelines/${selectedPipeline.id}/steps/${stepId}`, { method: "DELETE" });
      const updated = await api<Pipeline>(`/api/v1/pipelines/${selectedPipeline.id}`);
      setSelectedPipeline(updated);
      await fetchPipelines();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove step");
    }
  };

  const handleExecute = async () => {
    if (!selectedPipeline) return;
    setExecuting(true);
    setExecuteResult(null);
    try {
      const inputData = JSON.parse(executeInput);
      const run = await api<PipelineRun>(`/api/v1/pipelines/${selectedPipeline.id}/execute`, {
        method: "POST",
        body: JSON.stringify({ input_data: inputData }),
      });
      setExecuteResult(run);
      const data = await api<{ runs: PipelineRun[] }>(`/api/v1/pipelines/${selectedPipeline.id}/runs`);
      setRuns(data.runs);
      await fetchPipelines();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execution failed");
    } finally {
      setExecuting(false);
    }
  };

  const handleReorder = async (reordered: PipelineStep[]) => {
    if (!selectedPipeline) return;
    const updated = { ...selectedPipeline, steps: reordered.map((s, i) => ({ ...s, order: i })) };
    setSelectedPipeline(updated);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Pipelines</h1>
          <p className="text-white/40 mt-1">Chain agents together for multi-step workflows</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-[#C8FF00] text-[#050505] rounded-xl font-medium hover:bg-[#C8FF00]/90 transition-colors"
        >
          + New Pipeline
        </button>
      </div>

      {/* Error banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex justify-between"
          >
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400/60 hover:text-red-400">✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Pipelines", value: stats.total_pipelines, icon: "⟟" },
            { label: "Total Runs", value: stats.total_runs, icon: "▶" },
            { label: "Completed", value: stats.completed_runs, icon: "✓" },
            { label: "Failed", value: stats.failed_runs, icon: "✕" },
          ].map((s) => (
            <div key={s.label} className="p-4 bg-[#0A0A0A] border border-white/[0.06] rounded-xl">
              <div className="flex items-center gap-2 text-white/40 text-sm mb-1">
                <span>{s.icon}</span>
                <span>{s.label}</span>
              </div>
              <div className="text-2xl font-bold text-white">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Pipeline list */}
        <div className="col-span-1 space-y-3">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider">All Pipelines</h2>
          {loading ? (
            <div className="text-white/20 text-sm py-8 text-center">Loading...</div>
          ) : pipelines.length === 0 ? (
            <div className="text-white/20 text-sm py-8 text-center border border-dashed border-white/10 rounded-xl">
              No pipelines yet. Create one to get started.
            </div>
          ) : (
            <div className="space-y-2">
              {pipelines.map((p) => (
                <motion.div
                  key={p.id}
                  whileHover={{ scale: 1.01 }}
                  onClick={() => selectPipeline(p)}
                  className={`p-4 rounded-xl border cursor-pointer transition-colors ${
                    selectedPipeline?.id === p.id
                      ? "bg-[#C8FF00]/5 border-[#C8FF00]/20"
                      : "bg-[#0A0A0A] border-white/[0.06] hover:border-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white font-medium text-sm truncate">{p.name}</span>
                    <StatusBadge status={p.status} />
                  </div>
                  <p className="text-white/30 text-xs truncate">{p.description || "No description"}</p>
                  <div className="flex items-center gap-2 mt-2 text-white/20 text-xs">
                    <span>{p.steps.length} step{p.steps.length !== 1 ? "s" : ""}</span>
                    <span>·</span>
                    <span>{new Date(p.created_at).toLocaleDateString()}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline detail */}
        <div className="col-span-2 space-y-6">
          {selectedPipeline ? (
            <>
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">{selectedPipeline.name}</h2>
                  <p className="text-white/30 text-sm">{selectedPipeline.description}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowExecute(!showExecute)}
                    className="px-3 py-1.5 bg-[#C8FF00]/10 text-[#C8FF00] border border-[#C8FF00]/20 rounded-lg text-sm font-medium hover:bg-[#C8FF00]/20 transition-colors"
                  >
                    ▶ Execute
                  </button>
                  <button
                    onClick={() => handleDelete(selectedPipeline.id)}
                    className="px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm hover:bg-red-500/20 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Execute panel */}
              <AnimatePresence>
                {showExecute && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-4 bg-[#0A0A0A] border border-white/[0.06] rounded-xl space-y-3">
                      <label className="text-xs text-white/40 uppercase tracking-wider">Input JSON</label>
                      <textarea
                        value={executeInput}
                        onChange={(e) => setExecuteInput(e.target.value)}
                        rows={4}
                        className="w-full bg-[#050505] border border-white/[0.06] rounded-lg p-3 text-white text-sm font-mono focus:outline-none focus:border-[#C8FF00]/30"
                        placeholder='{"key": "value"}'
                      />
                      <button
                        onClick={handleExecute}
                        disabled={executing}
                        className="px-4 py-2 bg-[#C8FF00] text-[#050505] rounded-lg font-medium text-sm hover:bg-[#C8FF00]/90 transition-colors disabled:opacity-50"
                      >
                        {executing ? "Running..." : "Run Pipeline"}
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Execute result */}
              {executeResult && (
                <div className="p-4 bg-[#0A0A0A] border border-white/[0.06] rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/40">Latest Run</span>
                    <StatusBadge status={executeResult.status} />
                  </div>
                  <div className="text-xs text-white/30">
                    Duration: {executeResult.total_duration_ms.toFixed(1)}ms
                  </div>
                  <div className="space-y-2">
                    {executeResult.step_results.map((sr, i) => (
                      <div key={sr.step_id} className="flex items-center gap-3 p-2 bg-[#050505] rounded-lg">
                        <StepResultDot status={sr.status} />
                        <span className="text-sm text-white/60">Step {i + 1}</span>
                        <StatusBadge status={sr.status} />
                        <span className="text-xs text-white/20 ml-auto">{sr.duration_ms.toFixed(0)}ms</span>
                        {sr.error && <span className="text-xs text-red-400 truncate max-w-[200px]">{sr.error}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Steps editor */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-white/40 uppercase tracking-wider">Steps</h3>
                {selectedPipeline.steps.length === 0 ? (
                  <div className="text-white/20 text-sm py-6 text-center border border-dashed border-white/10 rounded-xl">
                    No steps yet. Add an agent step below.
                  </div>
                ) : (
                  <Reorder.Group
                    axis="y"
                    values={selectedPipeline.steps}
                    onReorder={handleReorder}
                    className="space-y-2"
                  >
                    {selectedPipeline.steps
                      .sort((a, b) => a.order - b.order)
                      .map((step, idx) => (
                        <Reorder.Item key={step.id} value={step}>
                          <div className="flex items-center gap-3 p-3 bg-[#0A0A0A] border border-white/[0.06] rounded-xl group">
                            <div className="cursor-grab text-white/20 hover:text-white/40">⠿</div>
                            <div className="w-7 h-7 rounded-lg bg-[#C8FF00]/10 flex items-center justify-center text-[#C8FF00] text-xs font-bold">
                              {idx + 1}
                            </div>
                            {idx > 0 && (
                              <div className="absolute -mt-8 ml-6 w-px h-3 bg-white/10" />
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="text-sm text-white font-medium truncate">{step.name}</div>
                              <div className="text-xs text-white/30 truncate">Agent: {step.agent_id}</div>
                            </div>
                            {step.condition && (
                              <span className="text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full">
                                conditional
                              </span>
                            )}
                            <div className="text-xs text-white/20">{step.timeout_seconds}s timeout</div>
                            <button
                              onClick={() => handleRemoveStep(step.id)}
                              className="opacity-0 group-hover:opacity-100 text-red-400/60 hover:text-red-400 text-sm transition-opacity"
                            >
                              ✕
                            </button>
                          </div>
                        </Reorder.Item>
                      ))}
                  </Reorder.Group>
                )}

                {/* Add step */}
                <div className="flex gap-2">
                  <input
                    value={addStepAgentId}
                    onChange={(e) => setAddStepAgentId(e.target.value)}
                    placeholder="Agent ID"
                    className="flex-1 bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#C8FF00]/30"
                  />
                  <input
                    value={addStepName}
                    onChange={(e) => setAddStepName(e.target.value)}
                    placeholder="Step name"
                    className="flex-1 bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#C8FF00]/30"
                  />
                  <button
                    onClick={handleAddStep}
                    className="px-3 py-2 bg-white/5 border border-white/[0.06] rounded-lg text-white/60 text-sm hover:bg-white/10 transition-colors"
                  >
                    + Add Step
                  </button>
                </div>
              </div>

              {/* Run history */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-white/40 uppercase tracking-wider">Run History</h3>
                {runs.length === 0 ? (
                  <div className="text-white/20 text-sm py-4 text-center">No runs yet</div>
                ) : (
                  <div className="space-y-2">
                    {runs.map((run) => (
                      <div key={run.id} className="p-3 bg-[#0A0A0A] border border-white/[0.06] rounded-xl">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <StatusBadge status={run.status} />
                            <span className="text-xs text-white/30 font-mono">{run.id.slice(0, 8)}</span>
                          </div>
                          <span className="text-xs text-white/20">{run.total_duration_ms.toFixed(1)}ms</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {run.step_results.map((sr) => (
                            <StepResultDot key={sr.step_id} status={sr.status} />
                          ))}
                        </div>
                        <div className="text-xs text-white/20 mt-1">
                          {new Date(run.started_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-64 text-white/20 text-sm border border-dashed border-white/10 rounded-xl">
              Select a pipeline to view details
            </div>
          )}
        </div>
      </div>

      {/* Create modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center"
            onClick={(e) => e.target === e.currentTarget && setShowCreate(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6 w-full max-w-lg space-y-4"
            >
              <h2 className="text-xl font-bold text-white">Create Pipeline</h2>
              <div className="space-y-3">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Pipeline name"
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-[#C8FF00]/30"
                  autoFocus
                />
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Description (optional)"
                  rows={2}
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-[#C8FF00]/30"
                />

                {/* Initial steps */}
                <div className="space-y-2">
                  <label className="text-xs text-white/40 uppercase tracking-wider">Initial Steps (optional)</label>
                  {newSteps.map((s, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <input
                        value={s.agent_id}
                        onChange={(e) => {
                          const updated = [...newSteps];
                          updated[i] = { ...updated[i], agent_id: e.target.value };
                          setNewSteps(updated);
                        }}
                        placeholder="Agent ID"
                        className="flex-1 bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-[#C8FF00]/30"
                      />
                      <input
                        value={s.name}
                        onChange={(e) => {
                          const updated = [...newSteps];
                          updated[i] = { ...updated[i], name: e.target.value };
                          setNewSteps(updated);
                        }}
                        placeholder="Step name"
                        className="flex-1 bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-[#C8FF00]/30"
                      />
                      <button
                        onClick={() => setNewSteps(newSteps.filter((_, j) => j !== i))}
                        className="text-red-400/60 hover:text-red-400 text-sm"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => setNewSteps([...newSteps, { agent_id: "", name: "" }])}
                    className="text-xs text-white/30 hover:text-white/60 transition-colors"
                  >
                    + Add step
                  </button>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-white/40 hover:text-white/60 text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={!newName.trim()}
                  className="px-4 py-2 bg-[#C8FF00] text-[#050505] rounded-lg font-medium text-sm hover:bg-[#C8FF00]/90 transition-colors disabled:opacity-50"
                >
                  Create Pipeline
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
