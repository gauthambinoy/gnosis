"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";

// ─── Quick Templates ───
const TEMPLATES = [
  {
    icon: "📧",
    label: "Email Automation",
    prompt:
      "Monitor my inbox every hour and summarize important emails, then send me a daily digest at 9 AM",
  },
  {
    icon: "🔍",
    label: "Web Monitor",
    prompt:
      "Monitor https://example.com every 6 hours and alert me when the content changes",
  },
  {
    icon: "📊",
    label: "Daily Report",
    prompt:
      "Generate a daily summary report of key metrics every morning and email it to team@company.com",
  },
  {
    icon: "🕷️",
    label: "Web Scraper",
    prompt:
      "Scrape product prices from https://shop.example.com daily and track changes in a spreadsheet",
  },
  {
    icon: "💬",
    label: "Chatbot",
    prompt:
      "Create a customer support chatbot that answers questions about our product using our FAQ knowledge base",
  },
  {
    icon: "📱",
    label: "Social Media",
    prompt:
      "Schedule and post content to Twitter and LinkedIn twice a day with engaging copywriting",
  },
  {
    icon: "🔬",
    label: "Research",
    prompt:
      "Research and compare the top 5 competitors in the AI agent space, analyze their features and pricing",
  },
  {
    icon: "✍️",
    label: "Content Writer",
    prompt:
      "Write a weekly blog article about AI trends, generate drafts every Monday morning",
  },
];

// ─── Types ───
interface DeploymentPlan {
  id: string;
  status: string;
  user_input: string;
  analysis: {
    detected_intents: string[];
    confidence: number;
    entities: Record<string, unknown>;
    suggested_name: string;
  };
  agents: Array<{
    name: string;
    description: string;
    model: string;
    tools_needed: string[];
  }>;
  pipeline: {
    name: string;
    steps: Array<{ name: string; order: number }>;
  } | null;
  schedule: {
    cron: string;
    description: string;
    timezone: string;
  } | null;
  integrations: Array<{ type: string; config: Record<string, unknown> }>;
  estimated_cost_per_run: string;
  created_at: number;
  deployed_at: number;
  created_agent_ids: string[];
}

// ─── Heading Typing Animation ───
function TypingHeading() {
  const text = "What do you want to automate?";
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    let i = 0;
    const iv = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) {
        clearInterval(iv);
        setDone(true);
      }
    }, 40);
    return () => clearInterval(iv);
  }, []);

  return (
    <h1 className="text-4xl md:text-5xl lg:text-6xl font-display font-bold text-gnosis-text text-center leading-tight">
      {displayed}
      {!done && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
          className="text-[#C8FF00]"
        >
          |
        </motion.span>
      )}
      {done && (
        <motion.span
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 300 }}
          className="inline-block ml-2"
        >
          ✨
        </motion.span>
      )}
    </h1>
  );
}

// ─── Confidence Meter ───
function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "#C8FF00" : pct >= 40 ? "#D4AF37" : "#ff6b6b";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
      <span className="text-sm font-mono" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}

// ─── Main Page ───
export default function FactoryPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [plan, setPlan] = useState<DeploymentPlan | null>(null);
  const [deployedPlan, setDeployedPlan] = useState<DeploymentPlan | null>(null);
  const [deployments, setDeployments] = useState<DeploymentPlan[]>([]);
  const [error, setError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadDeployments();
  }, []);

  async function loadDeployments() {
    try {
      const res = await api.fetch("/factory/deployments");
      if (res.ok) {
        setDeployments(await res.json());
      }
    } catch {
      // silent
    }
  }

  async function handleAnalyze() {
    if (!input.trim() || input.trim().length < 5) return;
    setLoading(true);
    setError("");
    setPlan(null);
    setDeployedPlan(null);

    try {
      const res = await api.fetch("/factory/analyze", {
        method: "POST",
        body: JSON.stringify({ description: input.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Analysis failed");
      }
      const data = await res.json();
      setPlan(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeploy() {
    if (!plan) return;
    setDeploying(true);
    setError("");

    try {
      const res = await api.fetch(`/factory/plans/${plan.id}/deploy`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Deployment failed");
      }
      const data = await res.json();
      setDeployedPlan(data);
      setPlan(null);
      loadDeployments();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Deployment failed");
    } finally {
      setDeploying(false);
    }
  }

  function handleTemplateClick(prompt: string) {
    setInput(prompt);
    setPlan(null);
    setDeployedPlan(null);
    textareaRef.current?.focus();
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <div className="mb-3">
          <span className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-[#C8FF00]/10 text-[#C8FF00] border border-[#C8FF00]/20">
            ✨ AGENT FACTORY
          </span>
        </div>
        <TypingHeading />
        <p className="mt-4 text-gnosis-muted text-lg max-w-xl mx-auto">
          Describe anything in plain English. Gnosis builds it for you.
        </p>
      </motion.div>

      {/* Input Area */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="max-w-3xl mx-auto mb-8"
      >
        <div className="relative group">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAnalyze();
            }}
            placeholder="e.g. Monitor https://news.ycombinator.com every hour and email me a summary of the top stories..."
            rows={4}
            className="w-full bg-[#0a0a0a] border border-white/10 rounded-2xl p-5 text-gnosis-text placeholder-white/20 resize-none focus:outline-none focus:border-[#C8FF00]/50 focus:shadow-[0_0_30px_rgba(200,255,0,0.1)] transition-all duration-300 text-base"
          />
          <div className="absolute bottom-3 right-3 text-xs text-white/20">
            ⌘+Enter to analyze
          </div>
        </div>

        <div className="mt-4 flex justify-center">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleAnalyze}
            disabled={loading || !input.trim() || input.trim().length < 5}
            className="relative px-8 py-3 rounded-xl font-semibold text-base bg-[#C8FF00] text-black disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-[0_0_30px_rgba(200,255,0,0.3)]"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="inline-block"
                >
                  ⚙
                </motion.span>
                Analyzing…
              </span>
            ) : (
              "✨ Create Agent"
            )}
          </motion.button>
        </div>
      </motion.div>

      {/* Quick Templates */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="max-w-4xl mx-auto mb-12"
      >
        <div className="flex flex-wrap justify-center gap-2">
          {TEMPLATES.map((t, i) => (
            <motion.button
              key={t.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + i * 0.05 }}
              whileHover={{ scale: 1.05, backgroundColor: "rgba(200,255,0,0.08)" }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleTemplateClick(t.prompt)}
              className="px-4 py-2 rounded-full border border-white/10 text-sm text-gnosis-muted hover:text-gnosis-text hover:border-[#C8FF00]/30 transition-all duration-200 bg-white/[0.02]"
            >
              {t.icon} {t.label}
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="max-w-3xl mx-auto mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Deployment Plan Preview */}
      <AnimatePresence>
        {plan && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
            className="max-w-3xl mx-auto mb-12"
          >
            <div className="rounded-2xl border border-[#C8FF00]/20 bg-[#0a0a0a] overflow-hidden">
              {/* Plan Header */}
              <div className="p-6 border-b border-white/5">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-gnosis-text mb-1">
                      {plan.analysis.suggested_name}
                    </h2>
                    <p className="text-sm text-gnosis-muted">
                      Deployment Plan • {plan.agents.length} agent
                      {plan.agents.length > 1 ? "s" : ""}
                    </p>
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/20">
                    {plan.status}
                  </span>
                </div>

                {/* Intent badges */}
                <div className="flex flex-wrap gap-2 mt-4">
                  {plan.analysis.detected_intents.map((intent: string) => (
                    <span
                      key={intent}
                      className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#C8FF00]/10 text-[#C8FF00] border border-[#C8FF00]/20"
                    >
                      {intent.replace("_", " ")}
                    </span>
                  ))}
                </div>

                {/* Confidence */}
                <div className="mt-4">
                  <p className="text-xs text-gnosis-muted mb-1.5">
                    Intent Confidence
                  </p>
                  <ConfidenceMeter value={plan.analysis.confidence} />
                </div>
              </div>

              {/* Agents */}
              <div className="p-6 border-b border-white/5">
                <h3 className="text-sm font-semibold text-gnosis-muted uppercase tracking-wider mb-3">
                  Agents to Create
                </h3>
                <div className="space-y-3">
                  {plan.agents.map((agent, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="p-4 rounded-xl bg-white/[0.02] border border-white/5"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gnosis-text text-sm">
                          {agent.name}
                        </span>
                        <span className="text-xs text-gnosis-muted px-2 py-0.5 rounded bg-white/5">
                          {agent.model}
                        </span>
                      </div>
                      <p className="text-xs text-gnosis-muted line-clamp-2">
                        {agent.description}
                      </p>
                      {agent.tools_needed.length > 0 && (
                        <div className="flex gap-1.5 mt-2">
                          {agent.tools_needed.map((tool) => (
                            <span
                              key={tool}
                              className="px-2 py-0.5 rounded text-[10px] bg-white/5 text-gnosis-muted"
                            >
                              {tool}
                            </span>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Pipeline */}
              {plan.pipeline && (
                <div className="p-6 border-b border-white/5">
                  <h3 className="text-sm font-semibold text-gnosis-muted uppercase tracking-wider mb-3">
                    Pipeline
                  </h3>
                  <div className="flex items-center gap-2 overflow-x-auto pb-2">
                    {plan.pipeline.steps.map(
                      (step: { name: string; order: number }, i: number) => (
                        <div key={i} className="flex items-center gap-2 shrink-0">
                          <div className="px-3 py-2 rounded-lg bg-[#C8FF00]/5 border border-[#C8FF00]/20 text-xs text-gnosis-text whitespace-nowrap">
                            {step.name}
                          </div>
                          {i < plan.pipeline!.steps.length - 1 && (
                            <span className="text-[#C8FF00]/40">→</span>
                          )}
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              {/* Schedule */}
              {plan.schedule && (
                <div className="p-6 border-b border-white/5">
                  <h3 className="text-sm font-semibold text-gnosis-muted uppercase tracking-wider mb-3">
                    Schedule
                  </h3>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🕐</span>
                    <div>
                      <p className="text-sm text-gnosis-text">
                        {plan.schedule.description}
                      </p>
                      <p className="text-xs text-gnosis-muted font-mono">
                        {plan.schedule.cron} ({plan.schedule.timezone})
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Integrations */}
              {plan.integrations.length > 0 && (
                <div className="p-6 border-b border-white/5">
                  <h3 className="text-sm font-semibold text-gnosis-muted uppercase tracking-wider mb-3">
                    Integrations
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {plan.integrations.map((integ, i) => (
                      <span
                        key={i}
                        className="px-3 py-1.5 rounded-lg text-xs bg-white/[0.03] border border-white/10 text-gnosis-muted"
                      >
                        {integ.type === "web_access" && "🌐 "}
                        {integ.type === "email" && "📧 "}
                        {integ.type === "notification" && "🔔 "}
                        {integ.type.replace("_", " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Cost + Deploy */}
              <div className="p-6 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gnosis-muted">Estimated cost per run</p>
                  <p className="text-sm text-gnosis-text font-mono">
                    {plan.estimated_cost_per_run}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => setPlan(null)}
                    className="px-4 py-2.5 rounded-xl text-sm border border-white/10 text-gnosis-muted hover:text-gnosis-text hover:border-white/20 transition-all"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleDeploy}
                    disabled={deploying}
                    className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-[#C8FF00] text-black hover:shadow-[0_0_30px_rgba(200,255,0,0.3)] disabled:opacity-50 transition-all"
                  >
                    {deploying ? (
                      <span className="flex items-center gap-2">
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{
                            duration: 1,
                            repeat: Infinity,
                            ease: "linear",
                          }}
                          className="inline-block"
                        >
                          ⚙
                        </motion.span>
                        Deploying…
                      </span>
                    ) : (
                      "🚀 Deploy Now"
                    )}
                  </motion.button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Deployed Success */}
      <AnimatePresence>
        {deployedPlan && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="max-w-3xl mx-auto mb-12"
          >
            <div className="rounded-2xl border border-[#C8FF00]/30 bg-[#C8FF00]/5 p-6 text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 300 }}
                className="text-5xl mb-4"
              >
                🚀
              </motion.div>
              <h2 className="text-2xl font-bold text-gnosis-text mb-2">
                Agent Deployed!
              </h2>
              <p className="text-gnosis-muted mb-4">
                {deployedPlan.created_agent_ids.length} agent
                {deployedPlan.created_agent_ids.length > 1 ? "s" : ""} created
                successfully
                {deployedPlan.schedule ? " with scheduled execution" : ""}
              </p>
              <div className="flex justify-center gap-3">
                <button
                  onClick={() => {
                    setDeployedPlan(null);
                    setInput("");
                  }}
                  className="px-5 py-2 rounded-xl text-sm bg-white/5 border border-white/10 text-gnosis-text hover:bg-white/10 transition-all"
                >
                  Create Another
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Recent Deployments */}
      {deployments.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="max-w-3xl mx-auto"
        >
          <h3 className="text-sm font-semibold text-gnosis-muted uppercase tracking-wider mb-4">
            Recent Deployments
          </h3>
          <div className="space-y-2">
            {deployments.slice(0, 10).map((dep) => (
              <div
                key={dep.id}
                className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-all"
              >
                <div className="min-w-0 flex-1 mr-4">
                  <p className="text-sm text-gnosis-text truncate">
                    {dep.analysis?.suggested_name || dep.user_input?.slice(0, 60)}
                  </p>
                  <p className="text-xs text-gnosis-muted mt-0.5">
                    {dep.created_agent_ids?.length || 0} agent
                    {(dep.created_agent_ids?.length || 0) > 1 ? "s" : ""} •{" "}
                    {new Date(dep.deployed_at * 1000).toLocaleDateString()}
                  </p>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium shrink-0 ${
                    dep.status === "deployed"
                      ? "bg-[#C8FF00]/10 text-[#C8FF00]"
                      : dep.status === "failed"
                      ? "bg-red-500/10 text-red-400"
                      : "bg-white/5 text-gnosis-muted"
                  }`}
                >
                  {dep.status}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
