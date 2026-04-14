"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Agent {
  agent_id: string;
  name: string;
  skills: string[];
  specialization: string;
  trust_score: number;
  availability: string;
  tasks_completed: number;
  success_rate: number;
}

interface SwarmTask {
  id: string;
  description: string;
  requester_id: string;
  required_skills: string[];
  assigned_agents: string[];
  status: string;
  subtasks: { id: string; description: string; status: string; assigned_to: string }[];
  results: { agent_id: string; result: Record<string, unknown> }[];
  consensus: { method: string; outcome: string; winner?: string } | null;
  reward_distribution: Record<string, number>;
}

interface SwarmMessage {
  id: string;
  from_agent: string;
  to_agent: string;
  message_type: string;
  content: Record<string, unknown>;
  timestamp: number;
}

interface Stats {
  registered_agents: number;
  available_agents: number;
  active_tasks: number;
  completed_tasks: number;
  total_messages: number;
}

type Tab = "registry" | "tasks" | "create" | "messages";

export default function SwarmPage() {
  const [tab, setTab] = useState<Tab>("registry");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<SwarmTask[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [messages, setMessages] = useState<SwarmMessage[]>([]);
  const [loading, setLoading] = useState(false);

  // Create task form
  const [taskDesc, setTaskDesc] = useState("");
  const [taskSkills, setTaskSkills] = useState("");
  const [taskRequester, setTaskRequester] = useState("");

  // Register form
  const [regId, setRegId] = useState("");
  const [regName, setRegName] = useState("");
  const [regSkills, setRegSkills] = useState("");
  const [regSpec, setRegSpec] = useState("");
  const [showRegister, setShowRegister] = useState(false);

  const [selectedInbox, setSelectedInbox] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [regRes, taskRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/swarm/registry`),
        fetch(`${API_BASE}/api/v1/swarm/tasks`),
        fetch(`${API_BASE}/api/v1/swarm/stats`),
      ]);
      if (regRes.ok) { const d = await regRes.json(); setAgents(d.agents || []); }
      if (taskRes.ok) { const d = await taskRes.json(); setTasks(d.tasks || []); }
      if (statsRes.ok) { const d = await statsRes.json(); setStats(d); }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const registerAgent = async () => {
    if (!regId.trim()) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/v1/swarm/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id: regId, name: regName || regId,
          skills: regSkills.split(",").map(s => s.trim()).filter(Boolean),
          specialization: regSpec || "general",
        }),
      });
      setRegId(""); setRegName(""); setRegSkills(""); setRegSpec("");
      setShowRegister(false);
      fetchData();
    } finally { setLoading(false); }
  };

  const unregisterAgent = async (id: string) => {
    await fetch(`${API_BASE}/api/v1/swarm/register/${id}`, { method: "DELETE" });
    fetchData();
  };

  const createTask = async () => {
    if (!taskDesc.trim()) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/v1/swarm/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: taskDesc,
          requester_id: taskRequester || "user",
          required_skills: taskSkills.split(",").map(s => s.trim()).filter(Boolean),
        }),
      });
      setTaskDesc(""); setTaskSkills(""); setTaskRequester("");
      fetchData();
      setTab("tasks");
    } finally { setLoading(false); }
  };

  const loadInbox = async (agentId: string) => {
    setSelectedInbox(agentId);
    try {
      const res = await fetch(`${API_BASE}/api/v1/swarm/inbox/${agentId}`);
      if (res.ok) { const d = await res.json(); setMessages(d.messages || []); }
    } catch { /* ignore */ }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "available": return "text-emerald-400";
      case "busy": return "text-amber-400";
      case "offline": return "text-red-400";
      case "active": return "text-blue-400";
      case "completed": return "text-emerald-400";
      case "recruiting": return "text-purple-400";
      case "voting": return "text-amber-400";
      case "open": return "text-gray-400";
      case "failed": return "text-red-400";
      default: return "text-gnosis-muted";
    }
  };

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "registry", label: "Agent Registry", icon: "👥" },
    { id: "tasks", label: "Swarm Tasks", icon: "📋" },
    { id: "create", label: "New Task", icon: "➕" },
    { id: "messages", label: "Messages", icon: "💬" },
  ];

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-gnosis-text">🐝 Agent Swarm</h1>
          <p className="text-gnosis-muted mt-1">Agents that discover, hire, and coordinate with each other</p>
        </div>
        <button
          onClick={() => setShowRegister(!showRegister)}
          className="px-4 py-2 bg-gnosis-primary/10 text-gnosis-primary rounded-xl text-sm font-medium hover:bg-gnosis-primary/20 transition-colors"
        >
          + Register Agent
        </button>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: "Registered", value: stats.registered_agents, icon: "👥" },
            { label: "Available", value: stats.available_agents, icon: "✅" },
            { label: "Active Tasks", value: stats.active_tasks, icon: "⚡" },
            { label: "Completed", value: stats.completed_tasks, icon: "✓" },
            { label: "Messages", value: stats.total_messages, icon: "💬" },
          ].map((s) => (
            <div key={s.label} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-3 text-center">
              <p className="text-lg">{s.icon}</p>
              <p className="text-xl font-bold text-gnosis-text">{s.value}</p>
              <p className="text-xs text-gnosis-muted">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Register Agent Modal */}
      <AnimatePresence>
        {showRegister && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-gnosis-surface border border-gnosis-border rounded-xl p-5 space-y-3 overflow-hidden"
          >
            <h3 className="text-sm font-semibold text-gnosis-text">Register New Agent</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input value={regId} onChange={e => setRegId(e.target.value)} placeholder="Agent ID *"
                className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              <input value={regName} onChange={e => setRegName(e.target.value)} placeholder="Display Name"
                className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              <input value={regSkills} onChange={e => setRegSkills(e.target.value)} placeholder="Skills (comma-separated)"
                className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              <input value={regSpec} onChange={e => setRegSpec(e.target.value)} placeholder="Specialization"
                className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
            </div>
            <div className="flex gap-2">
              <button onClick={registerAgent} disabled={loading || !regId.trim()}
                className="px-4 py-2 bg-gnosis-primary text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-gnosis-primary/90 transition-colors">
                Register
              </button>
              <button onClick={() => setShowRegister(false)}
                className="px-4 py-2 text-gnosis-muted text-sm hover:text-gnosis-text transition-colors">
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-gnosis-bg border border-gnosis-border w-fit">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`relative px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              tab === t.id ? "text-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
            }`}>
            {tab === t.id && (
              <motion.div layoutId="swarm-tab" className="absolute inset-0 bg-gnosis-primary/10 rounded-lg" transition={{ duration: 0.2 }} />
            )}
            <span className="relative z-10">{t.icon} {t.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {tab === "registry" && (
          <motion.div key="registry" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {agents.length === 0 && (
              <div className="col-span-full text-center py-16">
                <p className="text-4xl mb-3">🐝</p>
                <p className="text-gnosis-muted text-sm">No agents registered yet. Register one to start the swarm!</p>
              </div>
            )}
            {agents.map((agent) => (
              <div key={agent.agent_id} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gnosis-text text-sm">{agent.name}</h3>
                    <p className="text-xs text-gnosis-muted font-mono">{agent.agent_id}</p>
                  </div>
                  <span className={`text-xs font-medium ${statusColor(agent.availability)}`}>
                    ● {agent.availability}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {agent.skills.map((s) => (
                    <span key={s} className="px-2 py-0.5 bg-gnosis-primary/10 text-gnosis-primary rounded-md text-xs">{s}</span>
                  ))}
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div>
                    <p className="text-gnosis-text font-medium">{(agent.trust_score * 100).toFixed(0)}%</p>
                    <p className="text-gnosis-muted">Trust</p>
                  </div>
                  <div>
                    <p className="text-gnosis-text font-medium">{agent.tasks_completed}</p>
                    <p className="text-gnosis-muted">Tasks</p>
                  </div>
                  <div>
                    <p className="text-gnosis-text font-medium">{(agent.success_rate * 100).toFixed(0)}%</p>
                    <p className="text-gnosis-muted">Success</p>
                  </div>
                </div>
                <div className="flex justify-between items-center pt-1 border-t border-gnosis-border">
                  <span className="text-xs text-gnosis-muted">{agent.specialization}</span>
                  <div className="flex gap-2">
                    <button onClick={() => { setTab("messages"); loadInbox(agent.agent_id); }}
                      className="text-xs text-gnosis-primary hover:underline">Inbox</button>
                    <button onClick={() => unregisterAgent(agent.agent_id)}
                      className="text-xs text-red-400 hover:underline">Remove</button>
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {tab === "tasks" && (
          <motion.div key="tasks" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4">
            {tasks.length === 0 && (
              <div className="text-center py-16">
                <p className="text-4xl mb-3">📋</p>
                <p className="text-gnosis-muted text-sm">No swarm tasks yet. Create one to mobilize your agents!</p>
              </div>
            )}
            {tasks.map((task) => (
              <div key={task.id} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gnosis-text text-sm">{task.description}</h3>
                    <p className="text-xs text-gnosis-muted font-mono">ID: {task.id}</p>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-1 rounded-lg ${statusColor(task.status)} bg-current/10`}>
                    {task.status.toUpperCase()}
                  </span>
                </div>

                {task.required_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {task.required_skills.map((s) => (
                      <span key={s} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-md text-xs">{s}</span>
                    ))}
                  </div>
                )}

                {task.assigned_agents.length > 0 && (
                  <div>
                    <p className="text-xs text-gnosis-muted mb-1">Assigned Agents:</p>
                    <div className="flex flex-wrap gap-1">
                      {task.assigned_agents.map((a) => (
                        <span key={a} className="px-2 py-0.5 bg-gnosis-surface border border-gnosis-border rounded-md text-xs text-gnosis-text">{a}</span>
                      ))}
                    </div>
                  </div>
                )}

                {task.subtasks.length > 0 && (
                  <div>
                    <p className="text-xs text-gnosis-muted mb-1">Subtasks:</p>
                    <div className="space-y-1">
                      {task.subtasks.map((st) => (
                        <div key={st.id} className="flex items-center justify-between bg-gnosis-bg rounded-lg px-3 py-1.5 text-xs">
                          <span className="text-gnosis-text">{st.description}</span>
                          <span className={statusColor(st.status)}>{st.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {task.consensus && (
                  <div className="bg-gnosis-bg rounded-lg p-3 text-xs">
                    <p className="text-gnosis-muted">Consensus: <span className="text-gnosis-text">{task.consensus.outcome}</span></p>
                    {task.consensus.winner && <p className="text-gnosis-muted">Winner: <span className="text-emerald-400">{task.consensus.winner}</span></p>}
                  </div>
                )}

                {Object.keys(task.reward_distribution).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(task.reward_distribution).map(([agent, credit]) => (
                      <span key={agent} className="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-md text-xs">
                        {agent}: {credit} pts
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </motion.div>
        )}

        {tab === "create" && (
          <motion.div key="create" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="bg-gnosis-surface border border-gnosis-border rounded-xl p-6 space-y-4 max-w-2xl">
            <h3 className="font-semibold text-gnosis-text">Create Swarm Task</h3>
            <p className="text-xs text-gnosis-muted">Describe a task and the swarm will auto-recruit agents and decompose it into subtasks.</p>
            <div className="space-y-3">
              <textarea value={taskDesc} onChange={e => setTaskDesc(e.target.value)} rows={3}
                placeholder="Describe the task... (use 'and' to hint at subtasks)"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50 resize-none" />
              <input value={taskSkills} onChange={e => setTaskSkills(e.target.value)}
                placeholder="Required skills (comma-separated)"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              <input value={taskRequester} onChange={e => setTaskRequester(e.target.value)}
                placeholder="Requester ID (optional)"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              <button onClick={createTask} disabled={loading || !taskDesc.trim()}
                className="px-6 py-2 bg-gnosis-primary text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-gnosis-primary/90 transition-colors">
                🐝 Deploy Swarm
              </button>
            </div>
          </motion.div>
        )}

        {tab === "messages" && (
          <motion.div key="messages" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4">
            <div className="flex items-center gap-3">
              <select value={selectedInbox} onChange={e => loadInbox(e.target.value)}
                className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50">
                <option value="">Select agent inbox...</option>
                {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name} ({a.agent_id})</option>)}
              </select>
            </div>
            {messages.length === 0 && (
              <div className="text-center py-16">
                <p className="text-4xl mb-3">💬</p>
                <p className="text-gnosis-muted text-sm">{selectedInbox ? "No messages in this inbox" : "Select an agent to view their messages"}</p>
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gnosis-primary">{msg.from_agent}</span>
                    <span className="text-xs text-gnosis-muted">→</span>
                    <span className="text-xs text-gnosis-text">{msg.to_agent || "broadcast"}</span>
                  </div>
                  <span className="text-xs text-gnosis-muted px-2 py-0.5 bg-gnosis-bg rounded">{msg.message_type}</span>
                </div>
                <p className="text-xs text-gnosis-muted font-mono">{JSON.stringify(msg.content)}</p>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
