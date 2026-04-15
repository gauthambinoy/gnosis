"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";

// ─── Types ───

interface RpaAction {
  id: string;
  action_type: string;
  selector: string;
  value: string;
  description: string;
  page_url: string;
  element_tag: string;
  element_text: string;
  wait_before_ms: number;
  wait_after_ms: number;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  actions: RpaAction[];
  variables: Record<string, string>;
  start_url: string;
  tags: string[];
  status: string;
  run_count: number;
  last_run_status: string;
  last_run_at: number;
  avg_duration_ms: number;
  created_at: number;
  updated_at: number;
}

interface ExecutionResult {
  run_id: string;
  workflow_id: string;
  status: string;
  actions_total: number;
  actions_completed: number;
  actions_failed: number;
  duration_ms: number;
  logs: { action: string; selector: string; status: string; error?: string; index: number }[];
  extracted_data: Record<string, string>[];
  error: string;
}

interface Stats {
  total_workflows: number;
  active_recordings: number;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  playwright_available: boolean;
}

// ─── Action Icons ───

const ACTION_ICONS: Record<string, string> = {
  click: "🖱️",
  double_click: "🖱️",
  right_click: "🖱️",
  type: "⌨️",
  press_key: "⌨️",
  scroll: "📜",
  navigate: "🌐",
  wait: "⏳",
  wait_for_selector: "👁️",
  screenshot: "📸",
  select: "📋",
  hover: "👆",
  drag_drop: "✊",
  assert_text: "✅",
  assert_visible: "👁️",
  extract_text: "📤",
  extract_attribute: "🏷️",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "text-gray-400 bg-gray-400/10",
  active: "text-[#C8FF00] bg-[#C8FF00]/10",
  paused: "text-yellow-400 bg-yellow-400/10",
  archived: "text-gray-500 bg-gray-500/10",
  completed: "text-green-400 bg-green-400/10",
  completed_simulated: "text-blue-400 bg-blue-400/10",
  completed_with_errors: "text-yellow-400 bg-yellow-400/10",
  failed: "text-red-400 bg-red-400/10",
  running: "text-blue-400 bg-blue-400/10",
};

// ─── Component ───

export default function AutomationsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  // Recording state
  const [recordingSession, setRecordingSession] = useState<string | null>(null);
  const [recordedActions, setRecordedActions] = useState<RpaAction[]>([]);
  const [recordingStartTime, setRecordingStartTime] = useState(0);

  // UI state
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [showExecutionViewer, setShowExecutionViewer] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [scriptContent, setScriptContent] = useState<string | null>(null);
  const [showScript, setShowScript] = useState(false);

  // Create workflow form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState("");
  const [newWorkflowDesc, setNewWorkflowDesc] = useState("");
  const [newWorkflowUrl, setNewWorkflowUrl] = useState("");

  const fetchWorkflows = useCallback(async () => {
    try {
      const res = await api.get("/rpa/workflows");
      const data = await res.json();
      setWorkflows(data.workflows || []);
    } catch {
      /* ignore */
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get("/rpa/stats");
      setStats(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    Promise.all([fetchWorkflows(), fetchStats()]).finally(() => setLoading(false));
  }, [fetchWorkflows, fetchStats]);

  // Polling for recorded actions
  useEffect(() => {
    if (!recordingSession) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/rpa/record/${recordingSession}/actions`);
        const data = await res.json();
        setRecordedActions(data.actions || []);
      } catch {
        /* ignore */
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [recordingSession]);

  // ─── Recording ───

  const startRecording = async () => {
    try {
      const res = await api.post("/rpa/record/start", {});
      const data = await res.json();
      setRecordingSession(data.session_id);
      setRecordedActions([]);
      setRecordingStartTime(Date.now());
      fetchStats();
    } catch {
      /* ignore */
    }
  };

  const stopRecording = async () => {
    if (!recordingSession) return;
    try {
      const res = await api.post(`/rpa/record/${recordingSession}/stop`, { name: "", description: "" });
      await res.json();
      setRecordingSession(null);
      setRecordedActions([]);
      fetchWorkflows();
      fetchStats();
    } catch {
      /* ignore */
    }
  };

  // ─── Workflow Actions ───

  const createWorkflow = async () => {
    try {
      await api.post("/rpa/workflows", {
        name: newWorkflowName || "Untitled Workflow",
        description: newWorkflowDesc,
        start_url: newWorkflowUrl,
        actions: [],
      });
      setShowCreateForm(false);
      setNewWorkflowName("");
      setNewWorkflowDesc("");
      setNewWorkflowUrl("");
      fetchWorkflows();
      fetchStats();
    } catch {
      /* ignore */
    }
  };

  const executeWorkflow = async (id: string) => {
    setExecutingId(id);
    try {
      const res = await api.post(`/rpa/workflows/${id}/execute`, { variables: {} });
      const result = await res.json();
      setExecutionResult(result);
      setShowExecutionViewer(true);
      fetchWorkflows();
      fetchStats();
    } catch {
      /* ignore */
    } finally {
      setExecutingId(null);
    }
  };

  const duplicateWorkflow = async (id: string) => {
    try {
      await api.post(`/rpa/workflows/${id}/duplicate`);
      fetchWorkflows();
    } catch {
      /* ignore */
    }
  };

  const deleteWorkflow = async (id: string) => {
    try {
      await api.delete(`/rpa/workflows/${id}`);
      fetchWorkflows();
      fetchStats();
    } catch {
      /* ignore */
    }
  };

  const downloadScript = async (id: string) => {
    try {
      const res = await api.get(`/rpa/workflows/${id}/script`);
      const data = await res.json();
      setScriptContent(data.script);
      setShowScript(true);
    } catch {
      /* ignore */
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatTime = (ts: number) => {
    if (!ts) return "Never";
    return new Date(ts * 1000).toLocaleString();
  };

  // ─── Render ───

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            🤖 <span>Browser Automations</span>
          </h1>
          <p className="text-gray-400 mt-1">Record, replay, and automate browser workflows</p>
        </div>
        <div className="flex gap-3">
          {!recordingSession ? (
            <button
              onClick={startRecording}
              className="px-4 py-2.5 bg-[#C8FF00] text-black font-semibold rounded-xl hover:bg-[#d4ff33] transition-all duration-200 flex items-center gap-2"
            >
              <span className="w-2 h-2 rounded-full bg-red-500" />
              New Recording
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="px-4 py-2.5 bg-red-500/20 text-red-400 font-semibold rounded-xl hover:bg-red-500/30 transition-all duration-200 flex items-center gap-2 border border-red-500/30"
            >
              <motion.span
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 1 }}
                className="w-2 h-2 rounded-full bg-red-500"
              />
              Stop Recording
            </button>
          )}
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2.5 bg-white/5 text-white font-medium rounded-xl hover:bg-white/10 transition-all duration-200 border border-white/10"
          >
            + Create Workflow
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3"
        >
          {[
            { label: "Workflows", value: stats.total_workflows, icon: "📋" },
            { label: "Active Recordings", value: stats.active_recordings, icon: "⏺️" },
            { label: "Total Runs", value: stats.total_runs, icon: "▶️" },
            { label: "Completed", value: stats.completed_runs, icon: "✅" },
            { label: "Failed", value: stats.failed_runs, icon: "❌" },
            {
              label: "Playwright",
              value: stats.playwright_available ? "Ready" : "Simulated",
              icon: stats.playwright_available ? "🟢" : "🟡",
            },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-xl p-3 text-center"
            >
              <div className="text-lg">{stat.icon}</div>
              <div className="text-xl font-bold text-white mt-1">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      )}

      {/* Recording Panel */}
      <AnimatePresence>
        {recordingSession && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-red-500/5 border border-red-500/20 rounded-2xl p-6 overflow-hidden"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="w-3 h-3 rounded-full bg-red-500"
                />
                <span className="text-red-400 font-semibold text-lg">Recording...</span>
                <span className="text-gray-500 text-sm">
                  Session: {recordingSession}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-gray-400 text-sm">
                  {recordedActions.length} action{recordedActions.length !== 1 ? "s" : ""}
                </span>
                <button
                  onClick={stopRecording}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 transition-colors"
                >
                  ⏹ Stop & Save
                </button>
              </div>
            </div>

            <p className="text-gray-500 text-sm mb-4">
              Open your target website in another tab. Use the recorder widget or send actions via the API to capture your workflow.
            </p>

            {/* Live Action Feed */}
            {recordedActions.length > 0 && (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {recordedActions.map((action, i) => (
                  <motion.div
                    key={action.id || i}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3 bg-black/30 rounded-lg px-3 py-2 text-sm"
                  >
                    <span className="text-lg">{ACTION_ICONS[action.action_type] || "⚡"}</span>
                    <span className="text-[#C8FF00] font-mono text-xs">{action.action_type}</span>
                    {action.selector && (
                      <span className="text-gray-500 font-mono text-xs truncate max-w-[200px]">
                        {action.selector}
                      </span>
                    )}
                    {action.value && (
                      <span className="text-gray-400 text-xs truncate max-w-[150px]">
                        &quot;{action.value}&quot;
                      </span>
                    )}
                    {action.element_text && (
                      <span className="text-gray-600 text-xs truncate max-w-[100px]">
                        [{action.element_text}]
                      </span>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Create Workflow Form */}
      <AnimatePresence>
        {showCreateForm && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6"
          >
            <h3 className="text-lg font-semibold text-white mb-4">Create New Workflow</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Name</label>
                <input
                  value={newWorkflowName}
                  onChange={(e) => setNewWorkflowName(e.target.value)}
                  placeholder="My Automation"
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:border-[#C8FF00]/50 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Start URL</label>
                <input
                  value={newWorkflowUrl}
                  onChange={(e) => setNewWorkflowUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:border-[#C8FF00]/50 focus:outline-none transition-colors"
                />
              </div>
            </div>
            <div className="mb-4">
              <label className="text-sm text-gray-400 mb-1 block">Description</label>
              <textarea
                value={newWorkflowDesc}
                onChange={(e) => setNewWorkflowDesc(e.target.value)}
                placeholder="Describe what this automation does..."
                rows={2}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:border-[#C8FF00]/50 focus:outline-none transition-colors resize-none"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createWorkflow}
                className="px-4 py-2 bg-[#C8FF00] text-black font-semibold rounded-lg hover:bg-[#d4ff33] transition-colors"
              >
                Create Workflow
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Workflow List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
            className="w-8 h-8 border-2 border-[#C8FF00]/30 border-t-[#C8FF00] rounded-full"
          />
        </div>
      ) : workflows.length === 0 && !recordingSession ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-20"
        >
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Automations Yet</h3>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">
            Start by recording your browser actions or create a workflow manually. Automations can click, type, scroll, and extract data from any website.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={startRecording}
              className="px-5 py-2.5 bg-[#C8FF00] text-black font-semibold rounded-xl hover:bg-[#d4ff33] transition-colors"
            >
              ⏺️ Start Recording
            </button>
            <button
              onClick={() => setShowCreateForm(true)}
              className="px-5 py-2.5 bg-white/5 text-white rounded-xl hover:bg-white/10 transition-colors border border-white/10"
            >
              + Create Manually
            </button>
          </div>
        </motion.div>
      ) : (
        <div className="grid gap-4">
          {workflows.map((wf, i) => (
            <motion.div
              key={wf.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-5 hover:border-white/[0.12] transition-all duration-200 group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-lg font-semibold text-white truncate">{wf.name}</h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[wf.status] || "text-gray-400 bg-gray-400/10"}`}
                    >
                      {wf.status}
                    </span>
                  </div>
                  {wf.description && (
                    <p className="text-gray-500 text-sm mb-2 truncate">{wf.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    <span>📋 {wf.actions.length} actions</span>
                    <span>▶️ {wf.run_count} runs</span>
                    {wf.avg_duration_ms > 0 && (
                      <span>⏱️ ~{formatDuration(wf.avg_duration_ms)}</span>
                    )}
                    {wf.last_run_at > 0 && <span>🕐 Last: {formatTime(wf.last_run_at)}</span>}
                    {wf.last_run_status && (
                      <span
                        className={
                          STATUS_COLORS[wf.last_run_status]?.split(" ")[0] || "text-gray-500"
                        }
                      >
                        {wf.last_run_status}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => executeWorkflow(wf.id)}
                    disabled={executingId === wf.id}
                    className="p-2 bg-[#C8FF00]/10 text-[#C8FF00] rounded-lg hover:bg-[#C8FF00]/20 transition-colors disabled:opacity-50"
                    title="Run"
                  >
                    {executingId === wf.id ? (
                      <motion.span
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                        className="inline-block"
                      >
                        ⟳
                      </motion.span>
                    ) : (
                      "▶"
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setSelectedWorkflow(wf);
                      setShowEditor(true);
                    }}
                    className="p-2 bg-white/5 text-gray-400 rounded-lg hover:bg-white/10 hover:text-white transition-colors"
                    title="Edit"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => duplicateWorkflow(wf.id)}
                    className="p-2 bg-white/5 text-gray-400 rounded-lg hover:bg-white/10 hover:text-white transition-colors"
                    title="Duplicate"
                  >
                    📑
                  </button>
                  <button
                    onClick={() => downloadScript(wf.id)}
                    className="p-2 bg-white/5 text-gray-400 rounded-lg hover:bg-white/10 hover:text-white transition-colors"
                    title="Download Script"
                  >
                    📜
                  </button>
                  <button
                    onClick={() => deleteWorkflow(wf.id)}
                    className="p-2 bg-red-500/5 text-gray-400 rounded-lg hover:bg-red-500/10 hover:text-red-400 transition-colors"
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Workflow Editor Modal */}
      <AnimatePresence>
        {showEditor && selectedWorkflow && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setShowEditor(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Edit Workflow</h2>
                <button
                  onClick={() => setShowEditor(false)}
                  className="text-gray-500 hover:text-white transition-colors text-xl"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-sm text-gray-400 mb-1 block">Name</label>
                  <input
                    defaultValue={selectedWorkflow.name}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white focus:border-[#C8FF00]/50 focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-1 block">Start URL</label>
                  <input
                    defaultValue={selectedWorkflow.start_url}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white focus:border-[#C8FF00]/50 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Actions List */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">
                  Actions ({selectedWorkflow.actions.length})
                </h3>
                {selectedWorkflow.actions.length === 0 ? (
                  <p className="text-gray-600 text-sm py-4 text-center">
                    No actions yet. Record actions or add them manually.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {selectedWorkflow.actions.map((action: RpaAction, i: number) => (
                      <div
                        key={action.id || i}
                        className="flex items-center gap-3 bg-black/30 border border-white/[0.04] rounded-lg px-3 py-2"
                      >
                        <span className="text-gray-600 text-xs font-mono w-6 text-right">
                          {i + 1}
                        </span>
                        <span className="text-lg">
                          {ACTION_ICONS[action.action_type] || "⚡"}
                        </span>
                        <span className="text-[#C8FF00] font-mono text-xs min-w-[80px]">
                          {action.action_type}
                        </span>
                        {action.selector && (
                          <span className="text-gray-500 font-mono text-xs truncate flex-1">
                            {action.selector}
                          </span>
                        )}
                        {action.value && (
                          <span className="text-gray-400 text-xs truncate max-w-[150px]">
                            &quot;{action.value}&quot;
                          </span>
                        )}
                        <div className="flex gap-1 text-xs text-gray-600">
                          {action.wait_before_ms > 0 && (
                            <span>⏳{action.wait_before_ms}ms</span>
                          )}
                          {action.wait_after_ms > 0 && (
                            <span>⏱️{action.wait_after_ms}ms</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Variables */}
              {Object.keys(selectedWorkflow.variables).length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-400 mb-3">Variables</h3>
                  <div className="space-y-2">
                    {Object.entries(selectedWorkflow.variables).map(([key, val]) => (
                      <div
                        key={key}
                        className="flex items-center gap-2 bg-black/30 rounded-lg px-3 py-2"
                      >
                        <span className="text-[#C8FF00] font-mono text-xs">{`{{${key}}}`}</span>
                        <span className="text-gray-400 text-xs">= {String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowEditor(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Execution Viewer Modal */}
      <AnimatePresence>
        {showExecutionViewer && executionResult && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setShowExecutionViewer(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Execution Result</h2>
                <button
                  onClick={() => setShowExecutionViewer(false)}
                  className="text-gray-500 hover:text-white transition-colors text-xl"
                >
                  ✕
                </button>
              </div>

              {/* Status */}
              <div className="flex items-center gap-4 mb-6">
                <span
                  className={`text-sm px-3 py-1 rounded-full font-medium ${STATUS_COLORS[executionResult.status] || "text-gray-400 bg-gray-400/10"}`}
                >
                  {executionResult.status}
                </span>
                <span className="text-gray-500 text-sm">
                  Run ID: {executionResult.run_id}
                </span>
                {executionResult.duration_ms > 0 && (
                  <span className="text-gray-500 text-sm">
                    ⏱️ {formatDuration(executionResult.duration_ms)}
                  </span>
                )}
              </div>

              {/* Progress Bar */}
              <div className="mb-6">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>
                    {executionResult.actions_completed} / {executionResult.actions_total}{" "}
                    actions
                  </span>
                  {executionResult.actions_failed > 0 && (
                    <span className="text-red-400">
                      {executionResult.actions_failed} failed
                    </span>
                  )}
                </div>
                <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${executionResult.actions_total > 0 ? (executionResult.actions_completed / executionResult.actions_total) * 100 : 0}%`,
                    }}
                    className={`h-full rounded-full ${executionResult.actions_failed > 0 ? "bg-yellow-400" : "bg-[#C8FF00]"}`}
                  />
                </div>
              </div>

              {/* Error */}
              {executionResult.error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-6">
                  <p className="text-red-400 text-sm font-mono">{executionResult.error}</p>
                </div>
              )}

              {/* Log Feed */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">Execution Log</h3>
                <div className="space-y-1 max-h-60 overflow-y-auto">
                  {executionResult.logs.map((log, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs font-mono py-1"
                    >
                      <span className="text-gray-600 w-5 text-right">{log.index}</span>
                      <span
                        className={
                          log.status === "ok"
                            ? "text-green-400"
                            : log.status === "simulated"
                              ? "text-blue-400"
                              : "text-red-400"
                        }
                      >
                        {log.status === "ok" ? "✓" : log.status === "simulated" ? "◌" : "✗"}
                      </span>
                      <span className="text-[#C8FF00]">{log.action}</span>
                      {log.selector && (
                        <span className="text-gray-500 truncate">{log.selector}</span>
                      )}
                      {log.error && (
                        <span className="text-red-400 truncate">{log.error}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Extracted Data */}
              {executionResult.extracted_data.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-400 mb-3">
                    Extracted Data
                  </h3>
                  <div className="bg-black/30 rounded-lg overflow-hidden">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-white/[0.06]">
                          <th className="text-left px-3 py-2 text-gray-500">Index</th>
                          <th className="text-left px-3 py-2 text-gray-500">Selector</th>
                          <th className="text-left px-3 py-2 text-gray-500">Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {executionResult.extracted_data.map((d, i) => (
                          <tr key={i} className="border-b border-white/[0.03]">
                            <td className="px-3 py-2 text-gray-600">{d.index || i}</td>
                            <td className="px-3 py-2 text-gray-400 font-mono">
                              {d.selector}
                            </td>
                            <td className="px-3 py-2 text-white">
                              {d.text || d.value || "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={() => setShowExecutionViewer(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Script Viewer Modal */}
      <AnimatePresence>
        {showScript && scriptContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setShowScript(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">Generated Playwright Script</h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigator.clipboard.writeText(scriptContent)}
                    className="px-3 py-1.5 bg-white/5 text-gray-400 rounded-lg hover:bg-white/10 hover:text-white transition-colors text-sm"
                  >
                    📋 Copy
                  </button>
                  <button
                    onClick={() => setShowScript(false)}
                    className="text-gray-500 hover:text-white transition-colors text-xl"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <pre className="bg-black/50 border border-white/[0.06] rounded-lg p-4 text-sm text-gray-300 font-mono overflow-x-auto whitespace-pre">
                {scriptContent}
              </pre>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
