'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

interface CommandItem {
  id: string;
  title: string;
  subtitle?: string;
  icon?: string;
  action: () => void;
}

export function CommandPaletteMinimal() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const commands: CommandItem[] = [
    { id: 'agents', title: 'Go to Agents', icon: '🤖', subtitle: 'View all agents', action: () => router.push('/agents') },
    { id: 'create', title: 'Create Agent', icon: '➕', subtitle: 'Create a new agent', action: () => router.push('/agents/create') },
    { id: 'dashboard', title: 'Dashboard', icon: '📊', subtitle: 'Main dashboard', action: () => router.push('/') },
    { id: 'executions', title: 'Executions', icon: '⚡', subtitle: 'View executions', action: () => router.push('/executions') },
    { id: 'templates', title: 'Templates', icon: '📋', subtitle: 'Agent templates', action: () => router.push('/templates') },
    { id: 'settings', title: 'Settings', icon: '⚙️', subtitle: 'System settings', action: () => router.push('/settings') },
    { id: 'knowledge', title: 'Knowledge Base', icon: '🧠', subtitle: 'RAG knowledge', action: () => router.push('/knowledge') },
    { id: 'schedules', title: 'Schedules', icon: '🕐', subtitle: 'Scheduled tasks', action: () => router.push('/schedules') },
  ];

  const filtered = commands.filter(
    (c) => c.title.toLowerCase().includes(query.toLowerCase()) ||
           c.subtitle?.toLowerCase().includes(query.toLowerCase())
  );

  useKeyboardShortcuts([
    { key: 'k', meta: true, handler: () => setOpen((o) => !o) },
    { key: 'Escape', handler: () => setOpen(false) },
  ]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      filtered[selectedIndex].action();
      setOpen(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => setOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg bg-gray-900 border border-white/20 rounded-xl shadow-2xl z-50 overflow-hidden"
          >
            <div className="flex items-center gap-3 p-4 border-b border-white/10">
              <span className="text-white/40">🔍</span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
                onKeyDown={handleKeyDown}
                placeholder="Search commands..."
                className="flex-1 bg-transparent text-white placeholder-white/40 outline-none text-sm"
              />
              <kbd className="text-xs text-white/30 bg-white/10 px-2 py-1 rounded">ESC</kbd>
            </div>
            <div className="max-h-80 overflow-y-auto p-2">
              {filtered.map((cmd, i) => (
                <button
                  key={cmd.id}
                  onClick={() => { cmd.action(); setOpen(false); }}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                    i === selectedIndex ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5'
                  }`}
                >
                  <span className="text-lg">{cmd.icon}</span>
                  <div>
                    <p className="text-sm font-medium">{cmd.title}</p>
                    {cmd.subtitle && <p className="text-xs text-white/40">{cmd.subtitle}</p>}
                  </div>
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="text-center text-white/40 py-8 text-sm">No results found</p>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
