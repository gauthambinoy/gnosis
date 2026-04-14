"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";

/* ─── Types ─── */
interface Finding {
  severity: string;
  category: string;
  title: string;
  description: string;
  remediation: string;
}

interface ScanResult {
  score: number;
  grade: string;
  findings: Finding[];
  findings_count: Record<string, number>;
  security_headers: Record<string, boolean>;
  brute_force_lockouts: Record<string, number>;
}

interface ThreatEntry {
  time: number;
  ip: string;
  path?: string;
  type?: string;
  detail?: string;
  anomalies?: string[];
}

interface SecurityStats {
  total_requests: number;
  blocked_requests: number;
  block_rate: string;
  rate_limiter: {
    active_clients: number;
    blocked_ips: number;
    blocked_list: string[];
  };
  recent_threats: ThreatEntry[];
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getHeaders(): HeadersInit {
  let token: string | null = null;
  try {
    const raw = localStorage.getItem("auth-storage");
    if (raw) {
      const parsed = JSON.parse(raw);
      token = parsed?.state?.accessToken || null;
    }
  } catch {}
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function apiFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${API}${path}`, { ...opts, headers: { ...getHeaders(), ...opts.headers } });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

/* ─── Severity Badge ─── */
function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-400 border-red-500/30",
    high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    info: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  };
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-medium uppercase", colors[severity] || colors.info)}>
      {severity}
    </span>
  );
}

/* ─── Score Circle ─── */
function ScoreCircle({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "#22c55e" : score >= 50 ? "#eab308" : "#ef4444";

  return (
    <div className="relative w-36 h-36 flex items-center justify-center">
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
        <motion.circle
          cx="60" cy="60" r={radius} fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round" strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="text-center">
        <motion.span
          className="text-3xl font-bold"
          style={{ color }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {score}
        </motion.span>
        <p className="text-xs text-[var(--color-gnosis-muted)]">/ 100</p>
      </div>
    </div>
  );
}

/* ─── Header Checklist ─── */
function HeaderChecklist({ headers }: { headers: Record<string, boolean> }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {Object.entries(headers).map(([name, present]) => (
        <div key={name} className="flex items-center gap-2 text-sm">
          <span className={present ? "text-green-400" : "text-red-400"}>{present ? "✓" : "✗"}</span>
          <span className="text-[var(--color-gnosis-muted)] font-mono text-xs truncate">{name}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Main Page ─── */
export default function SecurityPage() {
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [blockIp, setBlockIp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiFetch("/security/stats");
      setStats(data);
      setLastRefresh(new Date());
    } catch {
      // API may not be available yet
    }
  }, []);

  const runScan = useCallback(async () => {
    setScanning(true);
    try {
      const data = await apiFetch("/security/scan", { method: "POST" });
      setScan(data);
    } catch (e) {
      setError("Scan failed — is the backend running?");
    } finally {
      setScanning(false);
    }
  }, []);

  const handleBlockIp = useCallback(async () => {
    if (!blockIp.trim()) return;
    try {
      await apiFetch("/security/block-ip", {
        method: "POST",
        body: JSON.stringify({ ip: blockIp.trim(), duration: 3600 }),
      });
      setBlockIp("");
      fetchStats();
    } catch {
      setError("Failed to block IP");
    }
  }, [blockIp, fetchStats]);

  const handleUnblockIp = useCallback(async (ip: string) => {
    try {
      await apiFetch("/security/unblock-ip", {
        method: "POST",
        body: JSON.stringify({ ip }),
      });
      fetchStats();
    } catch {
      setError("Failed to unblock IP");
    }
  }, [fetchStats]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    fetchStats();
    runScan();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, runScan]);

  const card = "bg-[var(--color-gnosis-surface)] border border-[var(--color-gnosis-border)] rounded-2xl p-6";

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-[var(--color-gnosis-text)] flex items-center gap-3">
            🛡️ Security Center
            {scan && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className={clsx(
                  "text-sm px-3 py-1 rounded-full font-medium",
                  scan.score >= 80 ? "bg-green-500/20 text-green-400" :
                  scan.score >= 50 ? "bg-yellow-500/20 text-yellow-400" :
                  "bg-red-500/20 text-red-400"
                )}
              >
                Grade: {scan.grade}
              </motion.span>
            )}
          </h1>
          <p className="text-[var(--color-gnosis-muted)] mt-1">
            Defense-in-depth security monitoring · Last refresh: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={runScan}
          disabled={scanning}
          className={clsx(
            "px-4 py-2 rounded-xl font-medium text-sm transition-all",
            scanning
              ? "bg-[var(--color-gnosis-primary)]/20 text-[var(--color-gnosis-primary)] cursor-wait"
              : "bg-[var(--color-gnosis-primary)] text-white hover:opacity-90"
          )}
        >
          {scanning ? "Scanning..." : "Run Security Scan"}
        </button>
      </motion.div>

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm flex items-center justify-between"
          >
            {error}
            <button onClick={() => setError(null)} className="ml-4 hover:text-red-300">✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Top row: Score + Threat Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Security Score Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={clsx(card, "flex flex-col items-center gap-4")}
        >
          <h2 className="text-lg font-semibold text-[var(--color-gnosis-text)] w-full">Security Score</h2>
          {scan ? (
            <>
              <ScoreCircle score={scan.score} />
              <div className="flex gap-3 flex-wrap justify-center">
                {Object.entries(scan.findings_count).map(([sev, count]) => (
                  count > 0 && (
                    <div key={sev} className="flex items-center gap-1.5">
                      <SeverityBadge severity={sev} />
                      <span className="text-xs text-[var(--color-gnosis-muted)]">×{count}</span>
                    </div>
                  )
                ))}
              </div>
            </>
          ) : (
            <div className="text-[var(--color-gnosis-muted)] text-sm py-8">Click &quot;Run Security Scan&quot; to begin</div>
          )}
        </motion.div>

        {/* Threat Monitor */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={clsx(card, "lg:col-span-2")}
        >
          <h2 className="text-lg font-semibold text-[var(--color-gnosis-text)] mb-4">Threat Monitor</h2>

          {/* Stats bar */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-[var(--color-gnosis-bg)] rounded-xl p-3 text-center">
              <p className="text-2xl font-bold text-[var(--color-gnosis-text)]">{stats?.total_requests ?? 0}</p>
              <p className="text-xs text-[var(--color-gnosis-muted)]">Total Requests</p>
            </div>
            <div className="bg-[var(--color-gnosis-bg)] rounded-xl p-3 text-center">
              <p className="text-2xl font-bold text-red-400">{stats?.blocked_requests ?? 0}</p>
              <p className="text-xs text-[var(--color-gnosis-muted)]">Blocked</p>
            </div>
            <div className="bg-[var(--color-gnosis-bg)] rounded-xl p-3 text-center">
              <p className="text-2xl font-bold text-[var(--color-gnosis-primary)]">{stats?.block_rate ?? "0%"}</p>
              <p className="text-xs text-[var(--color-gnosis-muted)]">Block Rate</p>
            </div>
          </div>

          {/* Threat feed */}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {stats?.recent_threats && stats.recent_threats.length > 0 ? (
              [...stats.recent_threats].reverse().map((threat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-3 bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2 text-sm"
                >
                  <span className="text-red-400 shrink-0">⚠</span>
                  <span className="text-[var(--color-gnosis-muted)] font-mono text-xs">{threat.ip}</span>
                  <span className="text-[var(--color-gnosis-text)] truncate flex-1">
                    {threat.type || threat.anomalies?.join(", ") || "Suspicious request"}
                  </span>
                  <span className="text-[var(--color-gnosis-muted)] text-xs shrink-0">
                    {threat.path || ""}
                  </span>
                </motion.div>
              ))
            ) : (
              <p className="text-[var(--color-gnosis-muted)] text-sm text-center py-4">No threats detected — all clear ✓</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Middle row: Findings + Headers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Findings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={card}
        >
          <h2 className="text-lg font-semibold text-[var(--color-gnosis-text)] mb-4">Scan Findings</h2>
          {scan?.findings && scan.findings.length > 0 ? (
            <div className="space-y-3">
              {scan.findings.map((f, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 + i * 0.05 }}
                  className="bg-[var(--color-gnosis-bg)] rounded-xl p-4 space-y-2"
                >
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <span className="text-sm font-medium text-[var(--color-gnosis-text)]">{f.title}</span>
                  </div>
                  <p className="text-xs text-[var(--color-gnosis-muted)]">{f.description}</p>
                  <p className="text-xs text-[var(--color-gnosis-primary)]">💡 {f.remediation}</p>
                </motion.div>
              ))}
            </div>
          ) : scan ? (
            <p className="text-green-400 text-sm text-center py-8">✓ No issues found — excellent security posture</p>
          ) : (
            <p className="text-[var(--color-gnosis-muted)] text-sm text-center py-8">Run a scan to see findings</p>
          )}
        </motion.div>

        {/* Security Headers */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className={card}
        >
          <h2 className="text-lg font-semibold text-[var(--color-gnosis-text)] mb-4">Security Headers</h2>
          {scan?.security_headers ? (
            <HeaderChecklist headers={scan.security_headers} />
          ) : (
            <p className="text-[var(--color-gnosis-muted)] text-sm text-center py-8">Run a scan to check headers</p>
          )}
        </motion.div>
      </div>

      {/* Bottom row: Rate Limiter + Brute Force */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rate Limiter / Blocked IPs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className={card}
        >
          <h2 className="text-lg font-semibold text-[var(--color-gnosis-text)] mb-4">Rate Limiter</h2>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-[var(--color-gnosis-bg)] rounded-xl p-3 text-center">
              <p className="text-xl font-bold text-[var(--color-gnosis-text)]">{stats?.rate_limiter?.active_clients ?? 0}</p>
              <p className="text-xs text-[var(--color-gnosis-muted)]">Active Clients</p>
            </div>
            <div className="bg-[var(--color-gnosis-bg)] rounded-xl p-3 text-center">
              <p className="text-xl font-bold text-red-400">{stats?.rate_limiter?.blocked_ips ?? 0}</p>
              <p className="text-xs text-[var(--color-gnosis-muted)]">Blocked IPs</p>
            </div>
          </div>

          {/* Block form */}
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              placeholder="IP address to block"
              value={blockIp}
              onChange={(e) => setBlockIp(e.target.value)}
              className="flex-1 bg-[var(--color-gnosis-bg)] border border-[var(--color-gnosis-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-gnosis-text)] placeholder:text-[var(--color-gnosis-muted)] focus:outline-none focus:border-[var(--color-gnosis-primary)]"
            />
            <button
              onClick={handleBlockIp}
              className="px-3 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg text-sm hover:bg-red-500/30 transition-colors"
            >
              Block
            </button>
          </div>

          {/* Blocked list */}
          <div className="space-y-2">
            {stats?.rate_limiter?.blocked_list?.map((ip) => (
              <div key={ip} className="flex items-center justify-between bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2">
                <span className="text-sm font-mono text-red-400">{ip}</span>
                <button
                  onClick={() => handleUnblockIp(ip)}
                  className="text-xs text-[var(--color-gnosis-muted)] hover:text-green-400 transition-colors"
                >
                  Unblock
                </button>
              </div>
            ))}
            {(!stats?.rate_limiter?.blocked_list || stats.rate_limiter.blocked_list.length === 0) && (
              <p className="text-[var(--color-gnosis-muted)] text-sm text-center py-2">No blocked IPs</p>
            )}
          </div>
        </motion.div>

        {/* Brute Force Monitor */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className={card}
        >
          <h2 className="text-lg font-semibold text-[var(--color-gnosis-text)] mb-4">Brute Force Monitor</h2>
          {scan?.brute_force_lockouts && Object.keys(scan.brute_force_lockouts).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(scan.brute_force_lockouts).map(([id, seconds]) => (
                <div key={id} className="flex items-center justify-between bg-orange-500/5 border border-orange-500/10 rounded-lg px-3 py-2">
                  <span className="text-sm font-mono text-orange-400">{id}</span>
                  <span className="text-xs text-[var(--color-gnosis-muted)]">
                    Locked for {Math.ceil(seconds / 60)}m
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-4xl mb-2">🔒</p>
              <p className="text-green-400 text-sm">No active lockouts</p>
              <p className="text-[var(--color-gnosis-muted)] text-xs mt-1">
                Accounts are locked after 5 failed attempts in 5 minutes
              </p>
            </div>
          )}

          <div className="mt-6 p-4 bg-[var(--color-gnosis-bg)] rounded-xl">
            <h3 className="text-sm font-medium text-[var(--color-gnosis-text)] mb-2">Protection Settings</h3>
            <div className="space-y-1 text-xs text-[var(--color-gnosis-muted)]">
              <p>• Max attempts: <span className="text-[var(--color-gnosis-text)]">5</span> per 5 min window</p>
              <p>• Lockout duration: <span className="text-[var(--color-gnosis-text)]">15 minutes</span></p>
              <p>• Rate limit: <span className="text-[var(--color-gnosis-text)]">100 req/min</span> per IP</p>
              <p>• Progressive blocking after <span className="text-[var(--color-gnosis-text)]">10</span> violations</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
