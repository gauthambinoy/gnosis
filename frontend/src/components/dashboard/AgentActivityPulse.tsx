'use client';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface ActiveAgent {
  agent_id: string;
  phase: string;
  timestamp: string;
}

export default function AgentActivityPulse({ wsUrl }: { wsUrl?: string }) {
  const [activeAgents, setActiveAgents] = useState<Map<string, ActiveAgent>>(new Map());

  useEffect(() => {
    const url = wsUrl || process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${url}/ws/dashboard`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'execution_phase') {
        setActiveAgents(prev => {
          const next = new Map(prev);
          if (data.data.status === 'completed' && data.phase === 'post') {
            next.delete(data.agent_id);
          } else {
            next.set(data.agent_id, { agent_id: data.agent_id, phase: data.phase, timestamp: data.timestamp });
          }
          return next;
        });
      }
    };

    return () => ws.close();
  }, [wsUrl]);

  if (activeAgents.size === 0) return null;

  return (
    <div className="flex items-center gap-1">
      {Array.from(activeAgents.values()).map(agent => (
        <motion.div
          key={agent.agent_id}
          className="w-3 h-3 rounded-full bg-[#C8FF00]"
          animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          title={`${agent.agent_id} — ${agent.phase}`}
        />
      ))}
      <span className="text-xs text-white/40 ml-1">{activeAgents.size} active</span>
    </div>
  );
}
