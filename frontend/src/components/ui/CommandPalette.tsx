"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";

interface Command {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  shortcut?: string;
  action: () => void;
  category: string;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const commands: Command[] = useMemo(
    () => [
      { id: "nav-home", label: "Go to Dashboard", icon: "🏠", category: "Navigation", shortcut: "G D", action: () => router.push("/") },
      { id: "nav-agents", label: "Go to Agents", icon: "🤖", category: "Navigation", shortcut: "G A", action: () => router.push("/awaken") },
      { id: "nav-pipelines", label: "Go to Pipelines", icon: "🔗", category: "Navigation", action: () => router.push("/pipelines") },
      { id: "nav-knowledge", label: "Go to Knowledge Base", icon: "📚", category: "Navigation", action: () => router.push("/knowledge") },
      { id: "nav-marketplace", label: "Go to Marketplace", icon: "🏪", category: "Navigation", action: () => router.push("/marketplace") },
      { id: "nav-security", label: "Go to Security", icon: "🛡️", category: "Navigation", action: () => router.push("/security") },
      { id: "nav-billing", label: "Go to Billing", icon: "💳", category: "Navigation", action: () => router.push("/billing") },
      { id: "nav-settings", label: "Go to Settings", icon: "⚙️", category: "Navigation", action: () => router.push("/settings") },
      { id: "nav-system", label: "Go to System Control", icon: "🖥️", category: "Navigation", action: () => router.push("/system") },
      { id: "nav-oracle", label: "Go to Oracle", icon: "🔮", category: "Navigation", action: () => router.push("/oracle") },
      { id: "nav-swarm", label: "Go to Swarm", icon: "🐝", category: "Navigation", action: () => router.push("/swarm") },
      { id: "nav-factory", label: "Go to Agent Factory", icon: "🏭", category: "Navigation", action: () => router.push("/factory") },
      { id: "nav-replay", label: "Go to Replay", icon: "⏪", category: "Navigation", action: () => router.push("/replay") },
      { id: "nav-dreams", label: "Go to Dreams", icon: "💭", category: "Navigation", action: () => router.push("/dreams") },
      { id: "act-new-agent", label: "Create New Agent", icon: "➕", category: "Actions", shortcut: "N", action: () => router.push("/awaken") },
      { id: "act-new-pipeline", label: "Create New Pipeline", icon: "🔗", category: "Actions", action: () => router.push("/pipelines") },
      { id: "act-docs", label: "Open API Documentation", icon: "📖", category: "Actions", action: () => window.open("/docs", "_blank") },
    ],
    [router]
  );

  const filtered = useMemo(() => {
    if (!query) return commands;
    const q = query.toLowerCase();
    return commands.filter(
      (c) => c.label.toLowerCase().includes(q) || c.category.toLowerCase().includes(q) || (c.description?.toLowerCase().includes(q))
    );
  }, [commands, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const execute = useCallback(
    (cmd: Command) => {
      setOpen(false);
      setQuery("");
      cmd.action();
    },
    []
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
        setQuery("");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filtered[selectedIndex]) {
      execute(filtered[selectedIndex]);
    }
  };

  const grouped = useMemo(() => {
    const groups: Record<string, Command[]> = {};
    for (const cmd of filtered) {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    }
    return groups;
  }, [filtered]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
          onClick={() => { setOpen(false); setQuery(""); }}
        >
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="w-full max-w-lg bg-[#0d1117] border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
              <span className="text-white/30 text-lg">⌘</span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a command or search..."
                className="flex-1 bg-transparent text-white text-sm outline-none placeholder:text-white/30"
              />
              <kbd className="text-[10px] text-white/20 border border-white/10 rounded px-1.5 py-0.5">ESC</kbd>
            </div>
            <div className="max-h-[50vh] overflow-y-auto py-2">
              {filtered.length === 0 ? (
                <p className="text-sm text-white/30 text-center py-8">No commands found</p>
              ) : (
                Object.entries(grouped).map(([category, cmds]) => (
                  <div key={category}>
                    <p className="text-[10px] uppercase tracking-wider text-white/20 px-4 py-1.5 font-semibold">{category}</p>
                    {cmds.map((cmd) => {
                      const globalIdx = filtered.indexOf(cmd);
                      return (
                        <button
                          key={cmd.id}
                          onClick={() => execute(cmd)}
                          onMouseEnter={() => setSelectedIndex(globalIdx)}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                            globalIdx === selectedIndex ? "bg-white/[0.06] text-white" : "text-white/60 hover:bg-white/[0.03]"
                          }`}
                        >
                          <span className="text-base w-6 text-center">{cmd.icon}</span>
                          <span className="flex-1">{cmd.label}</span>
                          {cmd.shortcut && (
                            <kbd className="text-[10px] text-white/20 border border-white/10 rounded px-1.5 py-0.5">{cmd.shortcut}</kbd>
                          )}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
