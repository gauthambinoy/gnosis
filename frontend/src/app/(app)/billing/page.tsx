"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { api } from "@/lib/api";

interface PlanInfo {
  tier: string;
  name: string;
  price: number;
  popular: boolean;
  limits: Record<string, number>;
}

interface UsageMetric {
  used: number;
  limit: number;
}

interface UsageSummary {
  plan: string;
  price: number;
  daily_executions: UsageMetric;
  monthly_tokens: UsageMetric;
  agents: UsageMetric;
  storage_mb: UsageMetric;
}

interface SubscriptionInfo {
  id: string;
  user_id: string;
  plan: string;
  status: string;
  current_period_start: string;
  created_at: string;
}

const LIMIT_LABELS: Record<string, string> = {
  agents: "Agents",
  executions_per_day: "Executions / day",
  tokens_per_month: "Tokens / month",
  file_storage_mb: "Storage (MB)",
  team_members: "Team members",
};

function formatLimit(value: number): string {
  if (value === -1) return "Unlimited";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(0)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return String(value);
}

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number }) {
  const isUnlimited = limit === -1;
  const pct = isUnlimited ? 0 : limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const color =
    pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-500" : "bg-gnosis-primary";

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-gnosis-muted">{label}</span>
        <span className="text-gnosis-text font-medium">
          {formatLimit(used)} / {isUnlimited ? "∞" : formatLimit(limit)}
        </span>
      </div>
      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: isUnlimited ? "2%" : `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={clsx("h-full rounded-full", color)}
        />
      </div>
    </div>
  );
}

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get("/billing/plans").then((r) => r.json()),
      api.get("/billing/usage").then((r) => r.json()),
      api.get("/billing/subscription").then((r) => r.json()),
    ])
      .then(([plansRes, usageRes, subRes]) => {
        setPlans(plansRes.plans || []);
        setUsage(usageRes.usage || null);
        setSubscription(subRes.subscription || null);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleUpgrade(tier: string) {
    setUpgrading(tier);
    try {
      const res = await api.post("/billing/subscribe", { plan: tier });
      const data = await res.json();
      setSubscription(data.subscription);
      // Refresh usage after plan change
      const usageRes = await api.get("/billing/usage").then((r) => r.json());
      setUsage(usageRes.usage || null);
    } catch (e) {
      console.error("Upgrade failed:", e);
    } finally {
      setUpgrading(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gnosis-muted">Loading billing…</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-gnosis-text">
          💳 Billing & Usage
        </h1>
        <p className="text-gnosis-muted mt-1">
          Manage your plan, track usage, and monitor quotas
        </p>
      </div>

      {/* Subscription Status */}
      {subscription && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-2xl border border-gnosis-border bg-gnosis-surface"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gnosis-muted">Current Plan</p>
              <p className="text-2xl font-bold text-gnosis-primary capitalize">
                {subscription.plan}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gnosis-muted">Status</p>
              <span
                className={clsx(
                  "inline-block px-3 py-1 rounded-full text-xs font-medium",
                  subscription.status === "active"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-red-500/10 text-red-400"
                )}
              >
                {subscription.status}
              </span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Plan Cards */}
      <div>
        <h2 className="text-lg font-semibold text-gnosis-text mb-4">Plans</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((plan, i) => {
            const isCurrent = subscription?.plan === plan.tier;
            return (
              <motion.div
                key={plan.tier}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className={clsx(
                  "relative p-5 rounded-2xl border bg-gnosis-surface flex flex-col",
                  plan.popular
                    ? "border-gnosis-primary shadow-[0_0_24px_rgba(var(--gnosis-primary-rgb),0.12)]"
                    : "border-gnosis-border",
                  isCurrent && "ring-2 ring-gnosis-primary/40"
                )}
              >
                {plan.popular && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-gnosis-primary text-black text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                    Popular
                  </span>
                )}

                <h3 className="text-lg font-bold text-gnosis-text capitalize">
                  {plan.name}
                </h3>
                <p className="mt-1 text-3xl font-display font-bold text-gnosis-text">
                  ${plan.price}
                  <span className="text-sm font-normal text-gnosis-muted">/mo</span>
                </p>

                <ul className="mt-4 space-y-2 flex-1 text-sm">
                  {Object.entries(plan.limits).map(([key, val]) => (
                    <li key={key} className="flex justify-between text-gnosis-muted">
                      <span>{LIMIT_LABELS[key] || key}</span>
                      <span className="text-gnosis-text font-medium">
                        {formatLimit(val as number)}
                      </span>
                    </li>
                  ))}
                </ul>

                <button
                  disabled={isCurrent || upgrading !== null}
                  onClick={() => handleUpgrade(plan.tier)}
                  className={clsx(
                    "mt-4 w-full py-2 rounded-xl text-sm font-medium transition-all",
                    isCurrent
                      ? "bg-gnosis-primary/10 text-gnosis-primary cursor-default"
                      : "bg-gnosis-primary text-black hover:brightness-110 disabled:opacity-50"
                  )}
                >
                  {isCurrent
                    ? "Current"
                    : upgrading === plan.tier
                      ? "Upgrading…"
                      : "Upgrade"}
                </button>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Usage Dashboard */}
      {usage && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 rounded-2xl border border-gnosis-border bg-gnosis-surface space-y-5"
        >
          <h2 className="text-lg font-semibold text-gnosis-text">Usage</h2>
          <UsageBar
            label="Daily Executions"
            used={usage.daily_executions.used}
            limit={usage.daily_executions.limit}
          />
          <UsageBar
            label="Monthly Tokens"
            used={usage.monthly_tokens.used}
            limit={usage.monthly_tokens.limit}
          />
          <UsageBar
            label="Agents"
            used={usage.agents.used}
            limit={usage.agents.limit}
          />
          <UsageBar
            label="Storage (MB)"
            used={usage.storage_mb.used}
            limit={usage.storage_mb.limit}
          />
        </motion.div>
      )}
    </div>
  );
}
