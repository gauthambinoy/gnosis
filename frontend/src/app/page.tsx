"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const PILLARS = [
  { icon: "✦", name: "The Awakening", desc: "Create agents through natural conversation — no code, no forms" },
  { icon: "◎", name: "The Cortex", desc: "5-layer brain: Perceive → Retrieve → Assemble → Reason → Meta" },
  { icon: "◈", name: "The Hippocampus", desc: "4-tier memory that learns and never forgets corrections" },
  { icon: "⟐", name: "The Cerebellum", desc: "3 learning loops: instant, pattern (6h), evolution (weekly)" },
  { icon: "◉", name: "Mind's Eye", desc: "Watch your agents think in real-time — live consciousness stream" },
  { icon: "⊛", name: "The Oracle", desc: "Proactive cross-agent insights and anomaly detection" },
  { icon: "⚡", name: "The Forge", desc: "Universal Action Protocol — connect any API in seconds" },
  { icon: "◇", name: "The Sanctum", desc: "Trust levels 0→3 that evolve with every interaction" },
  { icon: "∞", name: "The Chorus", desc: "Agent-to-agent communication and collaboration" },
  { icon: "◐", name: "Nerve Center", desc: "Real-time dashboard with breathing status orbs" },
  { icon: "☀", name: "Morning Standup", desc: "Daily AI briefing of everything your agents did" },
  { icon: "⟡", name: "Token Conservation", desc: "93.5% token reduction via progressive 4-tier reasoning" },
];

const STATS = [
  { value: "<5ms", label: "Memory retrieval" },
  { value: "93.5%", label: "Token savings" },
  { value: "4-tier", label: "Reasoning engine" },
  { value: "200+", label: "LLM models supported" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#050505] text-[#F0F0F0] overflow-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/[0.06] bg-[#050505]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-serif text-xl font-bold text-[#C8FF00]">◎ GNOSIS</span>
          <div className="flex items-center gap-6">
            <Link href="/login" className="text-sm text-[#888] hover:text-white transition-colors">Sign In</Link>
            <Link
              href="/signup"
              className="px-4 py-2 rounded-xl bg-[#C8FF00] text-[#050505] text-sm font-medium hover:shadow-[0_0_30px_rgba(200,255,0,0.3)] transition-all"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(200,255,0,0.04)_0%,transparent_70%)]" />
        <div className="max-w-4xl mx-auto text-center relative">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
            <p className="text-[#C8FF00] text-sm font-medium tracking-[0.3em] uppercase mb-6">
              The Knowledge That Works
            </p>
            <h1 className="font-serif text-6xl md:text-7xl lg:text-8xl font-bold leading-[0.95] mb-8">
              AI agents that{" "}
              <span className="text-[#C8FF00]">think</span>,{" "}
              <span className="text-[#D4AF37]">learn</span>,{" "}
              and <span className="text-[#C8FF00]">work</span>.
            </h1>
            <p className="text-xl text-[#888] max-w-2xl mx-auto leading-relaxed mb-12">
              Describe what you need in plain English. Gnosis creates an intelligent agent with
              its own brain, memory, and evolving trust — then executes flawlessly.
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
            className="flex items-center justify-center gap-4"
          >
            <Link
              href="/signup"
              className="px-8 py-4 rounded-xl bg-[#C8FF00] text-[#050505] font-semibold text-lg hover:shadow-[0_0_50px_rgba(200,255,0,0.3)] transition-all active:scale-[0.98]"
            >
              ✦ Awaken Your First Agent
            </Link>
            <Link
              href="#pillars"
              className="px-8 py-4 rounded-xl border border-[#1A1A1A] text-[#888] hover:text-white hover:border-[#333] transition-all"
            >
              Explore
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y border-white/[0.06] py-12">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-4 gap-8">
          {STATS.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <p className="text-3xl font-bold text-[#C8FF00] font-serif">{stat.value}</p>
              <p className="text-sm text-[#666] mt-1">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-serif text-4xl font-bold mb-4">Three steps. Zero complexity.</h2>
            <p className="text-[#888] text-lg">From thought to autonomous agent in under 60 seconds.</p>
          </motion.div>
          <div className="grid grid-cols-3 gap-8">
            {[
              { step: "01", title: "Describe", desc: "Tell Gnosis what you need in plain English. It asks smart clarifying questions." },
              { step: "02", title: "Awaken", desc: "Gnosis creates an agent with the right brain, memory, integrations, and guardrails." },
              { step: "03", title: "Evolve", desc: "Your agent learns from every interaction. Correct once — it never repeats the mistake." },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className="rounded-2xl border border-[#1A1A1A] bg-[#0A0A0A] p-8"
              >
                <span className="text-[#C8FF00] font-serif text-sm font-bold">{item.step}</span>
                <h3 className="text-xl font-bold mt-3 mb-3">{item.title}</h3>
                <p className="text-[#888] text-sm leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 12 Pillars */}
      <section id="pillars" className="py-24 px-6 border-t border-white/[0.06]">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-serif text-4xl font-bold mb-4">12 Pillars of Intelligence</h2>
            <p className="text-[#888] text-lg">Every pillar is unprecedented. Nothing like this exists.</p>
          </motion.div>
          <div className="grid grid-cols-3 gap-4">
            {PILLARS.map((pillar, i) => (
              <motion.div
                key={pillar.name}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="rounded-2xl border border-[#1A1A1A] bg-[#0A0A0A] p-6 hover:border-[#C8FF00]/20 hover:shadow-[0_0_40px_rgba(200,255,0,0.04)] transition-all duration-300"
              >
                <span className="text-2xl">{pillar.icon}</span>
                <h3 className="font-semibold mt-3 mb-2">{pillar.name}</h3>
                <p className="text-sm text-[#888] leading-relaxed">{pillar.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* LLM Gateway */}
      <section className="py-24 px-6 border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
            <h2 className="font-serif text-4xl font-bold mb-4">Universal LLM Gateway</h2>
            <p className="text-[#888] text-lg mb-12">One platform. Every model. Your choice.</p>
          </motion.div>
          <div className="flex flex-wrap justify-center gap-3">
            {["OpenRouter", "Claude", "GPT-4", "Gemini", "Groq", "Ollama", "Together AI", "Custom API"].map((model, i) => (
              <motion.div
                key={model}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="px-5 py-2.5 rounded-full border border-[#1A1A1A] bg-[#0A0A0A] text-sm text-[#888] hover:text-[#C8FF00] hover:border-[#C8FF00]/30 transition-all"
              >
                {model}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 border-t border-white/[0.06]">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <h2 className="font-serif text-5xl font-bold mb-6">
              Ready to <span className="text-[#C8FF00]">awaken</span>?
            </h2>
            <p className="text-[#888] text-lg mb-10">
              Join the next generation of intelligent automation. Free to start.
            </p>
            <Link
              href="/signup"
              className="inline-flex px-10 py-4 rounded-xl bg-[#C8FF00] text-[#050505] font-semibold text-lg hover:shadow-[0_0_60px_rgba(200,255,0,0.4)] transition-all active:scale-[0.98]"
            >
              ✦ Begin Your Journey
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.06] py-12 px-6">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <span className="font-serif text-lg font-bold text-[#C8FF00]">◎ GNOSIS</span>
            <p className="text-xs text-[#444] mt-1">The Knowledge That Works</p>
          </div>
          <p className="text-xs text-[#444]">Built with divine knowledge ◎</p>
        </div>
      </footer>
    </div>
  );
}
