"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/shared/Card";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { api } from "@/lib/api";

interface Template {
  id: string;
  name: string;
  emoji: string;
  description: string;
  category: string;
  integrations: string[];
  trigger: string;
  steps: string[];
  guardrails: string[];
  popularity: number;
}

const CATEGORIES = [
  { key: "all", label: "All" },
  { key: "productivity", label: "Productivity" },
  { key: "finance", label: "Finance" },
  { key: "team", label: "Team" },
  { key: "support", label: "Support" },
  { key: "marketing", label: "Marketing" },
  { key: "engineering", label: "Engineering" },
  { key: "security", label: "Security" },
];

const INTEGRATION_ICONS: Record<string, string> = {
  gmail: "✉️",
  slack: "💬",
  sheets: "📊",
  http: "🌐",
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] as const } },
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [deploying, setDeploying] = useState<string | null>(null);
  const [deployedIds, setDeployedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function fetchTemplates() {
      try {
        const res = await api.get("/templates");
        if (res.ok) {
          const data = await res.json();
          setTemplates(data.templates);
        }
      } catch {
        // API not available — use empty state
      } finally {
        setLoading(false);
      }
    }
    fetchTemplates();
  }, []);

  const filtered = useMemo(() => {
    let result = templates;
    if (activeCategory !== "all") {
      result = result.filter((t) => t.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q)
      );
    }
    return result.sort((a, b) => b.popularity - a.popularity);
  }, [templates, activeCategory, search]);

  async function handleDeploy(templateId: string) {
    setDeploying(templateId);
    try {
      const res = await api.post(`/templates/${templateId}/deploy`, {});
      if (res.ok) {
        setDeployedIds((prev) => new Set(prev).add(templateId));
      }
    } catch {
      // handle silently
    } finally {
      setDeploying(null);
    }
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div>
        <h1 className="font-display text-4xl font-bold text-gnosis-text">
          Pre-built Workflows
        </h1>
        <p className="text-gnosis-muted mt-2 text-lg">
          Deploy production-ready agents in seconds. Each template comes with pre-configured triggers, steps, and guardrails.
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gnosis-muted">⌕</span>
        <input
          type="text"
          placeholder="Search templates..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl border border-gnosis-border bg-gnosis-surface pl-11 pr-4 py-3 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary/50 transition-colors"
        />
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActiveCategory(cat.key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
              activeCategory === cat.key
                ? "bg-gnosis-primary text-gnosis-bg"
                : "border border-gnosis-border text-gnosis-muted hover:text-gnosis-text hover:border-gnosis-primary/40"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gnosis-muted">
          <p className="text-4xl mb-3">🔍</p>
          <p>No templates match your search.</p>
        </div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {filtered.map((t) => (
            <motion.div key={t.id} variants={cardVariants}>
              <Card glow className="flex flex-col h-full">
                {/* Header */}
                <div className="flex items-start gap-3 mb-3">
                  <span className="text-3xl">{t.emoji}</span>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-gnosis-text truncate">{t.name}</h3>
                    <Badge className="mt-1 capitalize">{t.category}</Badge>
                  </div>
                </div>

                {/* Description */}
                <p className="text-sm text-gnosis-muted leading-relaxed mb-4 flex-1">
                  {t.description}
                </p>

                {/* Integrations */}
                <div className="flex gap-2 mb-4">
                  {t.integrations.map((int_name) => (
                    <span
                      key={int_name}
                      className="inline-flex items-center gap-1 rounded-lg bg-white/[0.04] px-2 py-1 text-xs text-gnosis-muted"
                    >
                      {INTEGRATION_ICONS[int_name] || "🔗"} {int_name}
                    </span>
                  ))}
                </div>

                {/* Popularity */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-gnosis-muted mb-1">
                    <span>Popularity</span>
                    <span>{t.popularity}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-gnosis-border overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gnosis-primary"
                      initial={{ width: 0 }}
                      animate={{ width: `${t.popularity}%` }}
                      transition={{ duration: 0.8, delay: 0.2 }}
                    />
                  </div>
                </div>

                {/* Deploy Button */}
                {deployedIds.has(t.id) ? (
                  <Button variant="secondary" size="sm" disabled className="w-full">
                    ✓ Deployed
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => handleDeploy(t.id)}
                    disabled={deploying === t.id}
                  >
                    {deploying === t.id ? (
                      <span className="animate-pulse">Deploying...</span>
                    ) : (
                      "Deploy →"
                    )}
                  </Button>
                )}
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
