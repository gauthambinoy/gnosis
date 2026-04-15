"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import type { SystemInfo, ProcessInfo, DirectoryData, DockerData, AuditEntry } from "@/lib/types";

// ─── Helpers ───

function fmt(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}

function fmtTime(seconds: number) {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function fmtDate(ts: number) {
  return new Date(ts * 1000).toLocaleString();
}

async function apiFetch(path: string, opts?: RequestInit) {
  try {
    const method = opts?.method?.toUpperCase();
    let res: Response;
    if (method === "POST") {
      const body = opts?.body ? JSON.parse(opts.body as string) : undefined;
      res = await api.post(`/system-control${path}`, body);
    } else {
      res = await api.get(`/system-control${path}`);
    }
    return await res.json();
  } catch {
    return null;
  }
}

// ─── Circular Progress Ring ───

function CpuRing({ percent }: { percent: number }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const offset = circ - (percent / 100) * circ;
  const color = percent > 80 ? "#ef4444" : percent > 50 ? "#f59e0b" : "#22d3ee";
  return (
    <svg width="90" height="90" className="mx-auto">
      <circle cx="45" cy="45" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" />
      <circle
        cx="45" cy="45" r={r} fill="none" stroke={color} strokeWidth="7"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 45 45)"
        style={{ transition: "stroke-dashoffset 0.6s ease" }}
      />
      <text x="45" y="50" textAnchor="middle" fill={color} fontSize="16" fontWeight="bold">
        {percent.toFixed(0)}%
      </text>
    </svg>
  );
}

// ─── Progress Bar ───

function ProgressBar({ percent, color = "cyan" }: { percent: number; color?: string }) {
  const bg = color === "cyan" ? "bg-cyan-400" : color === "purple" ? "bg-purple-400" : "bg-amber-400";
  return (
    <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full ${bg} transition-all duration-500`}
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  );
}

// ─── Card Wrapper ───

function Card({ children, title, className = "" }: { children: React.ReactNode; title?: string; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5 ${className}`}
    >
      {title && <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">{title}</h3>}
      {children}
    </motion.div>
  );
}

// ─── File Viewer Modal ───

function FileModal({ path, onClose }: { path: string; onClose: () => void }) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch(`/files/read?path=${encodeURIComponent(path)}`).then((d) => {
      if (!d || d.detail) setError(d?.detail || "Failed to read file");
      else setContent(d.content);
    });
  }, [path]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-[#0d1117] border border-white/10 rounded-2xl w-[90vw] max-w-4xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <span className="text-cyan-400 font-mono text-sm truncate">{path}</span>
          <button onClick={onClose} className="text-white/40 hover:text-white text-lg">✕</button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          {error ? (
            <p className="text-red-400 text-sm">{error}</p>
          ) : content === null ? (
            <p className="text-white/30 text-sm">Loading...</p>
          ) : (
            <pre className="text-green-300/80 text-xs font-mono whitespace-pre-wrap">{content}</pre>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// ─── Main Page ───

export default function SystemControlPage() {
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const [dirData, setDirData] = useState<DirectoryData | null>(null);
  const [currentPath, setCurrentPath] = useState("/app");
  const [viewingFile, setViewingFile] = useState<string | null>(null);
  const [dockerData, setDockerData] = useState<DockerData | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [auditFilter, setAuditFilter] = useState("all");

  // Terminal state
  const [termInput, setTermInput] = useState("");
  const [termHistory, setTermHistory] = useState<any[]>([]);
  const [termHistIdx, setTermHistIdx] = useState(-1);
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const termEndRef = useRef<HTMLDivElement>(null);

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [processAutoRefresh, setProcessAutoRefresh] = useState(false);

  const loadSysInfo = useCallback(() => {
    apiFetch("/info").then((d) => d && setSysInfo(d));
  }, []);

  const loadProcesses = useCallback(() => {
    apiFetch("/processes").then((d) => d?.processes && setProcesses(d.processes));
  }, []);

  const loadDir = useCallback((path: string) => {
    setCurrentPath(path);
    apiFetch(`/files?path=${encodeURIComponent(path)}`).then((d) => d && setDirData(d));
  }, []);

  const loadDocker = useCallback(() => {
    apiFetch("/docker").then((d) => d && setDockerData(d));
  }, []);

  const loadAudit = useCallback(() => {
    apiFetch("/audit?limit=100").then((d) => d?.entries && setAuditLog(d.entries));
  }, []);

  // Initial load
  useEffect(() => {
    loadSysInfo();
    loadProcesses();
    loadDir("/app");
    loadDocker();
    loadAudit();
  }, [loadSysInfo, loadProcesses, loadDir, loadDocker, loadAudit]);

  // Auto-refresh system metrics
  useEffect(() => {
    if (!autoRefresh) return;
    const iv = setInterval(loadSysInfo, 10000);
    return () => clearInterval(iv);
  }, [autoRefresh, loadSysInfo]);

  // Auto-refresh processes
  useEffect(() => {
    if (!processAutoRefresh) return;
    const iv = setInterval(loadProcesses, 5000);
    return () => clearInterval(iv);
  }, [processAutoRefresh, loadProcesses]);

  // Scroll terminal to bottom
  useEffect(() => {
    termEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [termHistory]);

  // Execute terminal command
  const execCmd = async () => {
    const cmd = termInput.trim();
    if (!cmd) return;
    setCmdHistory((h) => [...h, cmd]);
    setTermHistIdx(-1);
    setTermInput("");

    const result = await apiFetch("/execute", {
      method: "POST",
      body: JSON.stringify({ command: cmd, timeout: 30 }),
    });

    setTermHistory((h) => [...h, { command: cmd, ...result }]);
    loadAudit();
  };

  const handleTermKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      execCmd();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (cmdHistory.length > 0) {
        const idx = termHistIdx < 0 ? cmdHistory.length - 1 : Math.max(0, termHistIdx - 1);
        setTermHistIdx(idx);
        setTermInput(cmdHistory[idx]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (termHistIdx >= 0) {
        const idx = termHistIdx + 1;
        if (idx >= cmdHistory.length) {
          setTermHistIdx(-1);
          setTermInput("");
        } else {
          setTermHistIdx(idx);
          setTermInput(cmdHistory[idx]);
        }
      }
    }
  };

  // Breadcrumb navigation
  const pathParts = currentPath.split("/").filter(Boolean);
  const breadcrumbs = pathParts.map((part, i) => ({
    name: part,
    path: "/" + pathParts.slice(0, i + 1).join("/"),
  }));

  const filteredAudit = auditFilter === "all"
    ? auditLog
    : auditLog.filter((e) => e.action === auditFilter);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold text-white">🖥️ System Control</h1>
          {sysInfo && (
            <span className="text-sm text-white/40 bg-white/5 px-3 py-1 rounded-full">
              {sysInfo.os}
            </span>
          )}
          {sysInfo && sysInfo.uptime_seconds > 0 && (
            <span className="text-sm text-cyan-400/70 bg-cyan-400/5 px-3 py-1 rounded-full">
              ⏱ {fmtTime(sysInfo.uptime_seconds)}
            </span>
          )}
        </div>
        <label className="flex items-center gap-2 text-sm text-white/40 cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="accent-cyan-400"
          />
          Auto-refresh (10s)
        </label>
      </div>

      {/* System Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU */}
        <Card title="CPU">
          {sysInfo ? (
            <>
              <CpuRing percent={sysInfo.cpu.usage_percent} />
              <p className="text-center text-white/40 text-xs mt-2">{sysInfo.cpu.cores} cores</p>
              {sysInfo.cpu.per_core && (
                <div className="flex gap-1 mt-3">
                  {sysInfo.cpu.per_core.map((v: number, i: number) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full bg-white/5 rounded-full h-12 relative overflow-hidden">
                        <div
                          className="absolute bottom-0 w-full bg-cyan-400/40 rounded-full transition-all duration-500"
                          style={{ height: `${v}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-white/30">{v}%</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-white/20 text-sm">Loading...</p>
          )}
        </Card>

        {/* Memory */}
        <Card title="Memory">
          {sysInfo ? (
            <>
              <div className="text-center mb-3">
                <span className="text-2xl font-bold text-purple-400">{sysInfo.memory.percent}%</span>
              </div>
              <ProgressBar percent={sysInfo.memory.percent} color="purple" />
              <div className="flex justify-between text-xs text-white/40 mt-2">
                <span>{sysInfo.memory.used_gb} GB used</span>
                <span>{sysInfo.memory.total_gb} GB total</span>
              </div>
              <p className="text-xs text-white/30 mt-1">
                {sysInfo.memory.available_gb} GB available
              </p>
            </>
          ) : (
            <p className="text-white/20 text-sm">Loading...</p>
          )}
        </Card>

        {/* Disk */}
        <Card title="Disk">
          {sysInfo ? (
            <>
              <div className="text-center mb-3">
                <span className="text-2xl font-bold text-amber-400">{sysInfo.disk.percent}%</span>
              </div>
              <ProgressBar percent={sysInfo.disk.percent} color="amber" />
              <div className="flex justify-between text-xs text-white/40 mt-2">
                <span>{sysInfo.disk.used_gb} GB used</span>
                <span>{sysInfo.disk.total_gb} GB total</span>
              </div>
              <p className="text-xs text-white/30 mt-1">
                {sysInfo.disk.free_gb} GB free
              </p>
            </>
          ) : (
            <p className="text-white/20 text-sm">Loading...</p>
          )}
        </Card>

        {/* Network */}
        <Card title="Network">
          {sysInfo?.network?.bytes_sent != null ? (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-white/40">Sent</p>
                <p className="text-lg font-semibold text-cyan-400">{fmt(sysInfo.network.bytes_sent)}</p>
              </div>
              <div>
                <p className="text-xs text-white/40">Received</p>
                <p className="text-lg font-semibold text-green-400">{fmt(sysInfo.network.bytes_recv)}</p>
              </div>
              <div className="flex justify-between text-xs text-white/30">
                <span>↑ {sysInfo.network.packets_sent?.toLocaleString()} pkts</span>
                <span>↓ {sysInfo.network.packets_recv?.toLocaleString()} pkts</span>
              </div>
            </div>
          ) : (
            <p className="text-white/20 text-sm">No network data</p>
          )}
        </Card>
      </div>

      {/* Terminal */}
      <Card title="Terminal">
        <div className="bg-black rounded-xl border border-white/[0.06] overflow-hidden">
          <div className="h-80 overflow-y-auto p-4 font-mono text-sm">
            {termHistory.length === 0 && (
              <p className="text-green-400/40">
                Type a whitelisted command below. Use ↑↓ for history.
              </p>
            )}
            {termHistory.map((item, i) => (
              <div key={i} className="mb-3">
                <div className="text-green-400">
                  <span className="text-green-600">$ </span>
                  {item.command}
                </div>
                {item.output && (
                  <pre className="text-green-300/70 whitespace-pre-wrap text-xs mt-1">{item.output}</pre>
                )}
                {item.error && (
                  <pre className="text-red-400/80 whitespace-pre-wrap text-xs mt-1">{item.error}</pre>
                )}
                <div className="text-white/20 text-xs mt-1">
                  exit={item.exit_code} duration={item.duration_ms?.toFixed(0)}ms
                </div>
              </div>
            ))}
            <div ref={termEndRef} />
          </div>
          <div className="flex items-center border-t border-white/[0.06] px-4 py-2 bg-white/[0.02]">
            <span className="text-green-500 font-mono mr-2">$</span>
            <input
              value={termInput}
              onChange={(e) => setTermInput(e.target.value)}
              onKeyDown={handleTermKey}
              className="flex-1 bg-transparent text-green-400 font-mono text-sm outline-none placeholder-green-400/30"
              placeholder="Enter command..."
              spellCheck={false}
            />
            <button
              onClick={() => setTermHistory([])}
              className="text-white/20 hover:text-white/50 text-xs ml-3"
            >
              Clear
            </button>
          </div>
        </div>
      </Card>

      {/* File Browser */}
      <Card title="File Browser">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-1 text-sm mb-4 flex-wrap">
          <button onClick={() => loadDir("/")} className="text-cyan-400 hover:text-cyan-300">/</button>
          {breadcrumbs.map((bc, i) => (
            <span key={bc.path} className="flex items-center gap-1">
              <span className="text-white/20">/</span>
              <button
                onClick={() => loadDir(bc.path)}
                className={i === breadcrumbs.length - 1 ? "text-white" : "text-cyan-400 hover:text-cyan-300"}
              >
                {bc.name}
              </button>
            </span>
          ))}
        </div>

        {dirData?.error ? (
          <p className="text-red-400 text-sm">{dirData.error}</p>
        ) : dirData?.entries ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/30 text-xs uppercase border-b border-white/5">
                  <th className="text-left py-2 px-2">Name</th>
                  <th className="text-left py-2 px-2">Type</th>
                  <th className="text-right py-2 px-2">Size</th>
                  <th className="text-right py-2 px-2">Modified</th>
                  <th className="text-right py-2 px-2">Perm</th>
                </tr>
              </thead>
              <tbody>
                {currentPath !== "/" && (
                  <tr
                    className="border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer"
                    onClick={() => loadDir(currentPath.split("/").slice(0, -1).join("/") || "/")}
                  >
                    <td className="py-1.5 px-2 text-cyan-400">..</td>
                    <td className="py-1.5 px-2 text-white/30">dir</td>
                    <td /><td /><td />
                  </tr>
                )}
                {dirData.entries.map((entry: any) => (
                  <tr
                    key={entry.name}
                    className="border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer"
                    onClick={() => {
                      if (entry.type === "dir") loadDir(`${currentPath === "/" ? "" : currentPath}/${entry.name}`);
                      else setViewingFile(`${currentPath === "/" ? "" : currentPath}/${entry.name}`);
                    }}
                  >
                    <td className={`py-1.5 px-2 ${entry.type === "dir" ? "text-cyan-400" : "text-white/70"}`}>
                      {entry.type === "dir" ? "📁 " : "📄 "}{entry.name}
                    </td>
                    <td className="py-1.5 px-2 text-white/30">{entry.type}</td>
                    <td className="py-1.5 px-2 text-right text-white/30">{entry.size != null ? fmt(entry.size) : ""}</td>
                    <td className="py-1.5 px-2 text-right text-white/30 text-xs">
                      {entry.modified ? new Date(entry.modified * 1000).toLocaleDateString() : ""}
                    </td>
                    <td className="py-1.5 px-2 text-right text-white/30 font-mono text-xs">{entry.permissions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-white/20 text-sm">Loading...</p>
        )}
      </Card>

      {/* Process Monitor */}
      <Card title="Process Monitor">
        <div className="flex justify-end mb-3">
          <label className="flex items-center gap-2 text-xs text-white/40 cursor-pointer">
            <input
              type="checkbox"
              checked={processAutoRefresh}
              onChange={(e) => setProcessAutoRefresh(e.target.checked)}
              className="accent-cyan-400"
            />
            Auto-refresh (5s)
          </label>
        </div>
        <div className="overflow-x-auto max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[#0d1117]">
              <tr className="text-white/30 text-xs uppercase border-b border-white/5">
                <th className="text-left py-2 px-2">PID</th>
                <th className="text-left py-2 px-2">Name</th>
                <th className="text-right py-2 px-2">CPU%</th>
                <th className="text-right py-2 px-2">Mem%</th>
                <th className="text-left py-2 px-2">Status</th>
                <th className="text-left py-2 px-2">User</th>
              </tr>
            </thead>
            <tbody>
              {processes.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-4 text-white/20">No data</td></tr>
              ) : processes.map((p: any) => (
                <tr key={p.pid} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                  <td className="py-1 px-2 font-mono text-white/50">{p.pid}</td>
                  <td className="py-1 px-2 text-white/70">{p.name}</td>
                  <td className="py-1 px-2 text-right">
                    <span className={p.cpu_percent > 50 ? "text-red-400" : p.cpu_percent > 10 ? "text-amber-400" : "text-white/50"}>
                      {p.cpu_percent?.toFixed(1)}
                    </span>
                  </td>
                  <td className="py-1 px-2 text-right text-white/50">{p.memory_percent?.toFixed(1)}</td>
                  <td className="py-1 px-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      p.status === "running" ? "bg-green-400/10 text-green-400" :
                      p.status === "sleeping" ? "bg-blue-400/10 text-blue-400" :
                      "bg-white/5 text-white/40"
                    }`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="py-1 px-2 text-white/40 text-xs">{p.user}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Docker Panel */}
      <Card title="Docker">
        {dockerData ? (
          <div className="space-y-4">
            <div className="flex items-center gap-4 text-sm">
              <span className={dockerData.status?.available ? "text-green-400" : "text-red-400"}>
                Docker: {dockerData.status?.available ? "Available" : "Not found"}
              </span>
            </div>
            {dockerData.containers?.output && (
              <div>
                <h4 className="text-xs text-white/40 uppercase mb-2">Containers</h4>
                <pre className="text-xs text-cyan-300/70 font-mono bg-black/40 p-3 rounded-lg whitespace-pre-wrap overflow-x-auto">
                  {dockerData.containers.output || "No containers running"}
                </pre>
              </div>
            )}
            {dockerData.stats?.output && (
              <div>
                <h4 className="text-xs text-white/40 uppercase mb-2">Resource Usage</h4>
                <pre className="text-xs text-green-300/70 font-mono bg-black/40 p-3 rounded-lg whitespace-pre-wrap overflow-x-auto">
                  {dockerData.stats.output}
                </pre>
              </div>
            )}
            {dockerData.containers?.error && !dockerData.containers?.output && (
              <p className="text-white/30 text-sm">No Docker containers detected. {dockerData.containers.error}</p>
            )}
          </div>
        ) : (
          <p className="text-white/20 text-sm">Loading...</p>
        )}
      </Card>

      {/* Audit Log */}
      <Card title="Audit Log">
        <div className="flex gap-2 mb-4 flex-wrap">
          {["all", "command_executed", "command_blocked"].map((f) => (
            <button
              key={f}
              onClick={() => setAuditFilter(f)}
              className={`text-xs px-3 py-1 rounded-full transition-colors ${
                auditFilter === f
                  ? "bg-cyan-400/20 text-cyan-400"
                  : "bg-white/5 text-white/40 hover:text-white/60"
              }`}
            >
              {f === "all" ? "All" : f.replace("_", " ")}
            </button>
          ))}
        </div>
        <div className="overflow-x-auto max-h-64 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[#0d1117]">
              <tr className="text-white/30 text-xs uppercase border-b border-white/5">
                <th className="text-left py-2 px-2">Time</th>
                <th className="text-left py-2 px-2">User</th>
                <th className="text-left py-2 px-2">Action</th>
                <th className="text-left py-2 px-2">Command</th>
                <th className="text-left py-2 px-2">Result</th>
              </tr>
            </thead>
            <tbody>
              {filteredAudit.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-4 text-white/20">No audit entries</td></tr>
              ) : filteredAudit.map((entry: any, i: number) => (
                <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                  <td className="py-1 px-2 text-white/30 text-xs whitespace-nowrap">{fmtDate(entry.timestamp)}</td>
                  <td className="py-1 px-2 text-white/50">{entry.user_id}</td>
                  <td className="py-1 px-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      entry.action === "command_blocked" ? "bg-red-400/10 text-red-400" : "bg-green-400/10 text-green-400"
                    }`}>
                      {entry.action}
                    </span>
                  </td>
                  <td className="py-1 px-2 text-white/60 font-mono text-xs max-w-xs truncate">{entry.detail}</td>
                  <td className="py-1 px-2 text-white/40 text-xs max-w-xs truncate">{entry.result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* File Viewer Modal */}
      <AnimatePresence>
        {viewingFile && <FileModal path={viewingFile} onClose={() => setViewingFile(null)} />}
      </AnimatePresence>
    </div>
  );
}
