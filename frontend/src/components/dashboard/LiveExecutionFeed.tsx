'use client';
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ExecutionEvent {
  type: string;
  agent_id: string;
  phase: string;
  data: { status: string; duration_ms?: number; [key: string]: unknown };
  timestamp: string;
}

const PHASE_COLORS: Record<string, string> = {
  perceive: '#C8FF00',
  memory: '#8B5CF6',
  context: '#3B82F6',
  reason: '#F59E0B',
  meta: '#EC4899',
  act: '#10B981',
  post: '#6366F1',
};

export default function LiveExecutionFeed() {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${wsUrl}/ws/dashboard`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect after 3s
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          setEvents([]);
        }
      }, 3000);
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'execution_phase') {
        setEvents(prev => [data, ...prev].slice(0, 50));
      }
    };

    // Keepalive ping every 30s
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 30000);

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, []);

  return (
    <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-white/70">Live Execution Feed</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-[#C8FF00] animate-pulse' : 'bg-red-500'}`} />
          <span className="text-xs text-white/40">{connected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>
      <div ref={feedRef} className="space-y-2 max-h-96 overflow-y-auto scrollbar-thin">
        <AnimatePresence initial={false}>
          {events.length === 0 ? (
            <p className="text-white/20 text-sm text-center py-8">Waiting for agent executions...</p>
          ) : (
            events.map((event, i) => (
              <motion.div
                key={`${event.timestamp}-${i}`}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-3 p-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.05] transition-colors"
              >
                <div
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: PHASE_COLORS[event.phase] || '#666' }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-white/50">{event.agent_id.slice(0, 8)}</span>
                    <span className="text-xs font-semibold" style={{ color: PHASE_COLORS[event.phase] || '#666' }}>
                      {event.phase}
                    </span>
                    <span className={`text-xs ${event.data.status === 'completed' ? 'text-green-400' : 'text-yellow-400'}`}>
                      {event.data.status}
                    </span>
                  </div>
                  {event.data.duration_ms && (
                    <span className="text-[10px] text-white/30">{Number(event.data.duration_ms).toFixed(1)}ms</span>
                  )}
                </div>
                <span className="text-[10px] text-white/20 flex-shrink-0">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
