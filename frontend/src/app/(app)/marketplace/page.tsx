"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { api } from "@/lib/api";

interface MarketplaceAgent {
  id: string;
  name: string;
  description: string;
  category: string;
  config: Record<string, unknown>;
  author: string;
  tags: string[];
  rating: number;
  rating_count: number;
  clone_count: number;
  featured: boolean;
  published_at: string;
}

interface Category {
  id: string;
  name: string;
  icon: string;
  description: string;
}

const SORT_OPTIONS = [
  { value: "popular", label: "Most Popular" },
  { value: "rating", label: "Top Rated" },
  { value: "newest", label: "Newest" },
  { value: "name", label: "Alphabetical" },
];

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-0.5 text-sm">
      {[1, 2, 3, 4, 5].map((s) => (
        <span key={s} className={s <= Math.round(rating) ? "text-[#D4AF37]" : "text-white/20"}>
          ★
        </span>
      ))}
      <span className="ml-1 text-white/50 text-xs">{rating.toFixed(1)}</span>
    </span>
  );
}

export default function MarketplacePage() {
  const [agents, setAgents] = useState<MarketplaceAgent[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("popular");
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const [total, setTotal] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState<MarketplaceAgent | null>(null);
  const [reviews, setReviews] = useState<Array<{ id: string; rating: number; comment: string; user_id: string; created_at: string }>>([]);
  const [showPublish, setShowPublish] = useState(false);
  const [loading, setLoading] = useState(true);
  const [cloneMessage, setCloneMessage] = useState<string | null>(null);

  // Publish form state
  const [pubName, setPubName] = useState("");
  const [pubDesc, setPubDesc] = useState("");
  const [pubCategory, setPubCategory] = useState("custom");
  const [pubTags, setPubTags] = useState("");
  const [pubPersona, setPubPersona] = useState("");

  // Review form state
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({ sort_by: sortBy, limit: "50" });
    if (selectedCategory) params.set("category", selectedCategory);
    if (search) params.set("search", search);
    if (featuredOnly) params.set("featured", "true");
    try {
      const res = await api.get(`/marketplace/browse?${params}`);
      const data = await res.json();
      setAgents(data.agents || []);
      setTotal(data.total || 0);
    } catch {
      /* ignore */
    }
    setLoading(false);
  }, [sortBy, selectedCategory, search, featuredOnly]);

  useEffect(() => {
    api.get("/marketplace/categories")
      .then((r) => r.json())
      .then((d) => setCategories(d.categories || []))
      .catch(() => {});
    api.get("/marketplace/stats")
      .then((r) => r.json())
      .then((d) => setStats(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  async function handleClone(agentId: string) {
    try {
      const res = await api.post(`/marketplace/${agentId}/clone`);
      if (res.ok) {
        setCloneMessage("Agent config cloned! Create a new agent with this config.");
        setTimeout(() => setCloneMessage(null), 3000);
      }
    } catch {
      /* ignore */
    }
  }

  async function handlePublish() {
    try {
      await api.post("/marketplace/publish", {
        name: pubName,
        description: pubDesc,
        category: pubCategory,
        config: { persona: pubPersona },
        tags: pubTags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setShowPublish(false);
      setPubName("");
      setPubDesc("");
      setPubTags("");
      setPubPersona("");
      fetchAgents();
    } catch {
      /* ignore */
    }
  }

  async function openDetail(agent: MarketplaceAgent) {
    setSelectedAgent(agent);
    try {
      const res = await api.get(`/marketplace/${agent.id}/reviews`);
      const data = await res.json();
      setReviews(data.reviews || []);
    } catch {
      setReviews([]);
    }
  }

  async function submitReview() {
    if (!selectedAgent) return;
    try {
      await api.post(`/marketplace/${selectedAgent.id}/reviews`, { rating: reviewRating, comment: reviewComment });
      setReviewComment("");
      const res = await api.get(`/marketplace/${selectedAgent.id}/reviews`);
      const data = await res.json();
      setReviews(data.reviews || []);
    } catch {
      /* ignore */
    }
  }

  const featuredAgents = agents.filter((a) => a.featured);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">
            🏪 <span className="text-[#C8FF00]">Marketplace</span>
          </h1>
          <p className="text-white/50 mt-1">
            Browse, publish, and clone community agents —{" "}
            <span className="text-[#C8FF00]">{stats.total_agents || 0}</span> agents available
          </p>
        </div>
        <button
          onClick={() => setShowPublish(true)}
          className="px-5 py-2.5 bg-[#C8FF00] text-[#050505] rounded-xl font-semibold hover:bg-[#C8FF00]/90 transition-colors"
        >
          + Publish Agent
        </button>
      </div>

      {/* Clone toast */}
      <AnimatePresence>
        {cloneMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="fixed top-6 right-6 z-50 bg-[#C8FF00] text-[#050505] px-5 py-3 rounded-xl font-medium shadow-lg"
          >
            {cloneMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Agents", value: stats.total_agents || 0, icon: "🤖" },
          { label: "Categories", value: stats.total_categories || 0, icon: "📂" },
          { label: "Featured", value: stats.featured_count || 0, icon: "⭐" },
          { label: "Total Clones", value: stats.total_clones || 0, icon: "📋" },
        ].map((s) => (
          <div key={s.label} className="bg-[#0A0A0A] border border-white/[0.06] rounded-xl p-4">
            <div className="text-2xl">{s.icon}</div>
            <div className="text-2xl font-bold text-white mt-1">{s.value}</div>
            <div className="text-sm text-white/40">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Category cards */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Categories</h2>
        <div className="grid grid-cols-4 lg:grid-cols-8 gap-3">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(selectedCategory === cat.id ? null : cat.id)}
              className={clsx(
                "flex flex-col items-center gap-1 p-3 rounded-xl border transition-all text-center",
                selectedCategory === cat.id
                  ? "border-[#C8FF00] bg-[#C8FF00]/10 text-[#C8FF00]"
                  : "border-white/[0.06] bg-[#0A0A0A] text-white/60 hover:border-white/20 hover:text-white"
              )}
            >
              <span className="text-2xl">{cat.icon}</span>
              <span className="text-xs font-medium truncate w-full">{cat.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Search & sort bar */}
      <div className="flex gap-4 items-center">
        <input
          type="text"
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-[#0A0A0A] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#C8FF00]/50"
        />
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="bg-[#0A0A0A] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-[#C8FF00]/50"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <button
          onClick={() => setFeaturedOnly(!featuredOnly)}
          className={clsx(
            "px-4 py-2.5 rounded-xl border text-sm font-medium transition-colors",
            featuredOnly
              ? "border-[#D4AF37] bg-[#D4AF37]/10 text-[#D4AF37]"
              : "border-white/[0.06] text-white/50 hover:text-white"
          )}
        >
          ⭐ Featured
        </button>
      </div>

      {/* Featured section */}
      {!selectedCategory && !search && featuredAgents.length > 0 && !featuredOnly && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <span className="text-[#D4AF37]">⭐</span> Featured Agents
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {featuredAgents.map((agent) => (
              <motion.div
                key={agent.id}
                whileHover={{ scale: 1.02 }}
                onClick={() => openDetail(agent)}
                className="bg-[#0A0A0A] border-2 border-[#D4AF37]/40 rounded-xl p-5 cursor-pointer hover:border-[#D4AF37] transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white">{agent.name}</h3>
                  <span className="text-xs bg-[#D4AF37]/20 text-[#D4AF37] px-2 py-0.5 rounded-full">Featured</span>
                </div>
                <p className="text-sm text-white/50 mb-3 line-clamp-2">{agent.description}</p>
                <div className="flex items-center justify-between">
                  <StarRating rating={agent.rating} />
                  <span className="text-xs text-white/30">{agent.clone_count} clones</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Agent grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">
            {selectedCategory ? categories.find((c) => c.id === selectedCategory)?.name || "Agents" : "All Agents"}
            <span className="text-white/30 text-sm ml-2">({total})</span>
          </h2>
        </div>
        {loading ? (
          <div className="text-center py-12 text-white/30">Loading agents...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <motion.div
                key={agent.id}
                whileHover={{ scale: 1.01 }}
                onClick={() => openDetail(agent)}
                className={clsx(
                  "bg-[#0A0A0A] border rounded-xl p-5 cursor-pointer transition-colors",
                  agent.featured ? "border-[#D4AF37]/30 hover:border-[#D4AF37]" : "border-white/[0.06] hover:border-white/20"
                )}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white">{agent.name}</h3>
                  <span className="text-xs bg-white/[0.06] text-white/50 px-2 py-0.5 rounded-full">{agent.category}</span>
                </div>
                <p className="text-sm text-white/50 mb-3 line-clamp-2">{agent.description}</p>
                {agent.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {agent.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="text-xs bg-[#C8FF00]/10 text-[#C8FF00]/70 px-2 py-0.5 rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between text-xs">
                  <StarRating rating={agent.rating} />
                  <span className="text-white/30">{agent.clone_count} clones</span>
                </div>
                <div className="flex items-center justify-between mt-2 text-xs text-white/30">
                  <span>by {agent.author}</span>
                  <span>{agent.rating_count} reviews</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Agent Detail Modal */}
      <AnimatePresence>
        {selectedAgent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedAgent(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-white">{selectedAgent.name}</h2>
                  <p className="text-white/40 text-sm mt-1">by {selectedAgent.author} · {selectedAgent.category}</p>
                </div>
                <button onClick={() => setSelectedAgent(null)} className="text-white/30 hover:text-white text-xl">✕</button>
              </div>
              <p className="text-white/60 mb-4">{selectedAgent.description}</p>
              <div className="flex items-center gap-4 mb-4">
                <StarRating rating={selectedAgent.rating} />
                <span className="text-sm text-white/30">{selectedAgent.rating_count} reviews</span>
                <span className="text-sm text-white/30">{selectedAgent.clone_count} clones</span>
              </div>
              {selectedAgent.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {selectedAgent.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-[#C8FF00]/10 text-[#C8FF00]/70 px-3 py-1 rounded-full">{tag}</span>
                  ))}
                </div>
              )}
              <button
                onClick={() => handleClone(selectedAgent.id)}
                className="w-full py-3 bg-[#C8FF00] text-[#050505] rounded-xl font-bold hover:bg-[#C8FF00]/90 transition-colors mb-6"
              >
                Clone Agent
              </button>

              {/* Reviews */}
              <div className="border-t border-white/[0.06] pt-4">
                <h3 className="text-lg font-semibold text-white mb-3">Reviews</h3>
                <div className="flex gap-3 mb-4">
                  <select
                    value={reviewRating}
                    onChange={(e) => setReviewRating(Number(e.target.value))}
                    className="bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2 text-white text-sm"
                  >
                    {[5, 4, 3, 2, 1].map((r) => (
                      <option key={r} value={r}>{"★".repeat(r)}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder="Write a review..."
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    className="flex-1 bg-[#050505] border border-white/[0.06] rounded-lg px-3 py-2 text-white text-sm placeholder-white/30 focus:outline-none"
                  />
                  <button onClick={submitReview} className="px-4 py-2 bg-[#C8FF00]/20 text-[#C8FF00] rounded-lg text-sm font-medium hover:bg-[#C8FF00]/30">
                    Submit
                  </button>
                </div>
                {reviews.length === 0 ? (
                  <p className="text-white/30 text-sm">No reviews yet. Be the first!</p>
                ) : (
                  <div className="space-y-3">
                    {reviews.map((rev) => (
                      <div key={rev.id} className="bg-[#050505] rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <StarRating rating={rev.rating} />
                          <span className="text-xs text-white/30">{rev.user_id}</span>
                        </div>
                        {rev.comment && <p className="text-sm text-white/60">{rev.comment}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Publish Modal */}
      <AnimatePresence>
        {showPublish && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowPublish(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-6 max-w-lg w-full"
            >
              <h2 className="text-xl font-bold text-white mb-4">Publish Agent to Marketplace</h2>
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Agent name"
                  value={pubName}
                  onChange={(e) => setPubName(e.target.value)}
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#C8FF00]/50"
                />
                <textarea
                  placeholder="Description"
                  value={pubDesc}
                  onChange={(e) => setPubDesc(e.target.value)}
                  rows={3}
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#C8FF00]/50 resize-none"
                />
                <select
                  value={pubCategory}
                  onChange={(e) => setPubCategory(e.target.value)}
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-[#C8FF00]/50"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Tags (comma-separated)"
                  value={pubTags}
                  onChange={(e) => setPubTags(e.target.value)}
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#C8FF00]/50"
                />
                <textarea
                  placeholder="Agent persona / system prompt"
                  value={pubPersona}
                  onChange={(e) => setPubPersona(e.target.value)}
                  rows={3}
                  className="w-full bg-[#050505] border border-white/[0.06] rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#C8FF00]/50 resize-none"
                />
              </div>
              <div className="flex gap-3 mt-5">
                <button
                  onClick={() => setShowPublish(false)}
                  className="flex-1 py-2.5 border border-white/[0.06] text-white/60 rounded-xl hover:bg-white/[0.03] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePublish}
                  disabled={!pubName || !pubDesc}
                  className="flex-1 py-2.5 bg-[#C8FF00] text-[#050505] rounded-xl font-semibold hover:bg-[#C8FF00]/90 transition-colors disabled:opacity-30"
                >
                  Publish
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
