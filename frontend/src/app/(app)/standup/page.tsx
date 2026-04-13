"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/shared/Card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StandupAgent {
  name: string;
  summary: string;
}

interface StandupData {
  total_actions: number;
  time_saved_minutes: number;
  accuracy: number;
  agents: StandupAgent[];
}

export default function StandupPage() {
  const [standup, setStandup] = useState<StandupData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStandup() {
      try {
        const res = await fetch(API_URL + "/api/v1/standup/today");
        if (res.ok) {
          setStandup(await res.json());
        }
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    }
    fetchStandup();
  }, []);

  const totalActions = standup?.total_actions || 0;
  const timeSavedMinutes = standup?.time_saved_minutes || 0;
  const accuracy = standup?.accuracy || 0;
  const agents = standup?.agents || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">◈ Morning Standup</h1>
        <p className="text-gnosis-muted mt-1">Daily briefing from your agent network</p>
      </div>

      {loading ? (
        <div className="h-48 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
      ) : (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <div className="flex items-center gap-3 mb-6">
              <span className="text-2xl">◈</span>
              <div>
                <h2 className="font-semibold text-gnosis-text">
                  {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
                </h2>
                <p className="text-xs text-gnosis-muted">
                  {totalActions} actions · {timeSavedMinutes}m saved · {(accuracy * 100).toFixed(0)}% accuracy
                </p>
              </div>
            </div>

            {agents.length ? (
              <div className="space-y-4">
                {agents.map((agent, i) => (
                  <div key={i} className="border-l-2 border-gnosis-primary/30 pl-4">
                    <h3 className="font-medium text-gnosis-text">{agent.name}</h3>
                    <p className="text-sm text-gnosis-muted mt-1">{agent.summary}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gnosis-muted text-center py-8">No agent activity yet. Create your first agent to see daily standups.</p>
            )}
          </Card>
        </motion.div>
      )}
    </div>
  );
}
