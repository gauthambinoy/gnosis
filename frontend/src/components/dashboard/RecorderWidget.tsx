"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Floating recorder widget — embed in any page to capture browser actions.
 * Shows as a small circle button in the bottom-right; expands when active.
 */
export default function RecorderWidget() {
  const [expanded, setExpanded] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [actionCount, setActionCount] = useState(0);
  const [startTime, setStartTime] = useState(0);
  const [elapsed, setElapsed] = useState("0:00");

  // Timer
  useEffect(() => {
    if (!sessionId || !startTime) return;
    const interval = setInterval(() => {
      const secs = Math.floor((Date.now() - startTime) / 1000);
      const m = Math.floor(secs / 60);
      const s = secs % 60;
      setElapsed(`${m}:${s.toString().padStart(2, "0")}`);
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionId, startTime]);

  // Poll action count
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/v1/rpa/record/${sessionId}/actions`);
        const data = await res.json();
        setActionCount(data.count || 0);
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const startRecording = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/rpa/record/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setActionCount(0);
      setStartTime(Date.now());
      setExpanded(true);
    } catch {
      /* ignore */
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API}/api/v1/rpa/record/${sessionId}/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "", description: "" }),
      });
    } catch {
      /* ignore */
    }
    setSessionId(null);
    setActionCount(0);
    setStartTime(0);
    setElapsed("0:00");
    setExpanded(false);
  }, [sessionId]);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <AnimatePresence mode="wait">
        {!expanded ? (
          /* Collapsed — circle button */
          <motion.button
            key="collapsed"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            onClick={() => {
              if (sessionId) {
                setExpanded(true);
              } else {
                startRecording();
              }
            }}
            className="w-14 h-14 rounded-full bg-[#0A0A0A] border border-white/10 flex items-center justify-center shadow-2xl hover:border-[#C8FF00]/50 hover:shadow-[#C8FF00]/10 transition-all duration-200 group relative"
            title="RPA Recorder"
          >
            {sessionId ? (
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
                className="w-4 h-4 rounded-full bg-red-500"
              />
            ) : (
              <span className="text-2xl group-hover:scale-110 transition-transform">⏺️</span>
            )}
            {sessionId && (
              <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#C8FF00] text-black text-[10px] font-bold flex items-center justify-center">
                {actionCount}
              </span>
            )}
          </motion.button>
        ) : (
          /* Expanded — recording controls */
          <motion.div
            key="expanded"
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            className="bg-[#0A0A0A] border border-white/10 rounded-2xl p-4 w-72 shadow-2xl"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1 }}
                  className="w-2.5 h-2.5 rounded-full bg-red-500"
                />
                <span className="text-red-400 font-semibold text-sm">Recording</span>
              </div>
              <button
                onClick={() => setExpanded(false)}
                className="text-gray-500 hover:text-white transition-colors text-sm"
              >
                ▾
              </button>
            </div>

            <div className="flex items-center justify-between mb-3 text-sm">
              <div className="text-gray-400">
                <span className="text-white font-semibold">{actionCount}</span>{" "}
                action{actionCount !== 1 ? "s" : ""}
              </div>
              <div className="text-gray-500 font-mono">{elapsed}</div>
            </div>

            <div className="text-xs text-gray-600 mb-3">
              Session: <span className="font-mono text-gray-500">{sessionId}</span>
            </div>

            <button
              onClick={stopRecording}
              className="w-full py-2 bg-red-500/20 text-red-400 rounded-lg font-medium hover:bg-red-500/30 transition-colors text-sm border border-red-500/20"
            >
              ⏹ Stop & Save
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
