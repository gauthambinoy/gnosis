"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Card } from "@/components/shared/Card";

const TRUST_LABELS = ["Observer", "Apprentice", "Associate", "Autonomous"];
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AgentData {
  name: string;
  description: string;
  status: string;
  avatar_emoji: string;
  trust_level: number;
  total_actions: number;
  total_executions: number;
  accuracy: number;
  time_saved_minutes: number;
}

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params?.id as string;
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAgent() {
      try {
        const res = await fetch(API_URL + "/api/v1/agents/" + agentId);
        if (res.ok) setAgent(await res.json());
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    }
    if (agentId) fetchAgent();
  }, [agentId]);

  if (loading) {
    return <div className="h-96 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />;
  }

  if (!agent) {
    return (
      <Card className="text-center py-16">
        <p className="text-gnosis-muted">Agent not found</p>
      </Card>
    );
  }

  const trustLevel = agent.trust_level || 0;
  const totalActions = agent.total_actions || agent.total_executions || 0;
  const accuracy = agent.accuracy || 0;
  const timeSavedMinutes = agent.time_saved_minutes || 0;

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-4 mb-2">
          <span className="text-4xl">{agent.avatar_emoji || "◎"}</span>
          <div>
            <h1 className="font-display text-3xl font-bold text-gnosis-text">{agent.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-sm text-gnosis-primary">{TRUST_LABELS[trustLevel]}</span>
              <span className="text-gnosis-muted">·</span>
              <span className="text-sm text-gnosis-muted capitalize">{agent.status}</span>
            </div>
          </div>
        </div>
        <p className="text-gnosis-muted">{agent.description}</p>
      </motion.div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Executions", value: totalActions },
          { label: "Accuracy", value: (accuracy * 100).toFixed(1) + "%" },
          { label: "Time Saved", value: timeSavedMinutes.toFixed(0) + "m" },
          { label: "Trust Level", value: "L" + trustLevel },
        ].map((m, i) => (
          <motion.div key={m.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <Card className="text-center">
              <p className="text-2xl font-bold text-gnosis-text">{m.value}</p>
              <p className="text-xs text-gnosis-muted mt-1">{m.label}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card>
        <h2 className="font-semibold text-gnosis-text mb-4">Mind&apos;s Eye — Consciousness Stream</h2>
        <div className="bg-gnosis-bg rounded-xl p-6 border border-gnosis-border min-h-[200px] flex items-center justify-center">
          <p className="text-gnosis-muted text-sm">Live consciousness stream will appear here when the agent is executing</p>
        </div>
      </Card>
    </div>
  );
}
