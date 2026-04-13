"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/shared/Card";

interface AgentCard {
  id: string;
  name: string;
  description: string;
  status: "active" | "idle" | "paused" | "error";
  trust_level: number;
  accuracy: number;
  total_executions: number;
  time_saved_minutes: number;
  avatar_emoji: string;
}

const TRUST_LABELS = ["Observer", "Apprentice", "Associate", "Autonomous"];
const STATUS_COLORS: Record<string, string> = {
  active: "bg-gnosis-primary",
  idle: "bg-gnosis-muted",
  paused: "bg-yellow-500",
  error: "bg-red-500",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function NerveCenterPage() {
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, active: 0, timeSaved: 0, accuracy: 0 });

  useEffect(() => {
    fetchAgents();
  }, []);

  async function fetchAgents() {
    try {
      const res = await fetch(API_URL + "/api/v1/agents");
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents || []);
        const agentList = data.agents || [];
        setStats({
          total: agentList.length,
          active: agentList.filter((a: AgentCard) => a.status === "active").length,
          timeSaved: agentList.reduce((s: number, a: AgentCard) => s + a.time_saved_minutes, 0),
          accuracy: agentList.length ? agentList.reduce((s: number, a: AgentCard) => s + a.accuracy, 0) / agentList.length : 0,
        });
      }
    } catch {
      // API not available yet
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">Nerve Center</h1>
        <p className="text-gnosis-muted mt-1">Real-time overview of your agent network</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Agents", value: stats.total, icon: "◎" },
          { label: "Active Now", value: stats.active, icon: "◉", highlight: true },
          { label: "Time Saved", value: stats.timeSaved.toFixed(0) + "m", icon: "⏱" },
          { label: "Accuracy", value: (stats.accuracy * 100).toFixed(1) + "%", icon: "◈" },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="text-center">
              <span className="text-2xl">{stat.icon}</span>
              <p className={"text-2xl font-bold mt-2 " + (stat.highlight ? "text-gnosis-primary" : "text-gnosis-text")}>
                {stat.value}
              </p>
              <p className="text-xs text-gnosis-muted mt-1">{stat.label}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gnosis-text">Your Agents</h2>
          <a href="/awaken" className="text-sm text-gnosis-primary hover:underline">+ Create Agent</a>
        </div>

        {loading ? (
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
            ))}
          </div>
        ) : agents.length === 0 ? (
          <Card className="text-center py-16">
            <p className="text-4xl mb-4">◎</p>
            <h3 className="text-xl font-display font-bold text-gnosis-text mb-2">No agents yet</h3>
            <p className="text-gnosis-muted mb-6">Describe what you need and Gnosis will create an intelligent agent for you.</p>
            <a
              href="/awaken"
              className="inline-flex items-center px-6 py-3 rounded-xl bg-gnosis-primary text-gnosis-bg font-medium hover:shadow-[0_0_30px_rgba(200,255,0,0.3)] transition-all"
            >
              ✦ Awaken Your First Agent
            </a>
          </Card>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {agents.map((agent, i) => (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <a href={"/agent/" + agent.id}>
                  <Card glow className="hover:border-gnosis-primary/30 transition-all cursor-pointer">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{agent.avatar_emoji}</span>
                        <div>
                          <h3 className="font-semibold text-gnosis-text">{agent.name}</h3>
                          <p className="text-xs text-gnosis-muted">{TRUST_LABELS[agent.trust_level]}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className={"w-2 h-2 rounded-full " + STATUS_COLORS[agent.status] + (agent.status === "active" ? " animate-pulse" : "")} />
                        <span className="text-xs text-gnosis-muted capitalize">{agent.status}</span>
                      </div>
                    </div>
                    <p className="text-sm text-gnosis-muted line-clamp-2 mb-4">{agent.description}</p>
                    <div className="flex justify-between text-xs text-gnosis-muted border-t border-gnosis-border pt-3">
                      <span>{agent.total_executions} runs</span>
                      <span>{(agent.accuracy * 100).toFixed(0)}% accuracy</span>
                      <span>{agent.time_saved_minutes.toFixed(0)}m saved</span>
                    </div>
                  </Card>
                </a>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
