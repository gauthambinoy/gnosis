'use client';
import { useTheme } from '@/lib/theme';
import { motion } from 'framer-motion';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const options = [
    { value: 'dark' as const, icon: '🌙', label: 'Dark' },
    { value: 'light' as const, icon: '☀️', label: 'Light' },
    { value: 'system' as const, icon: '💻', label: 'System' },
  ];

  return (
    <div className="flex items-center gap-1 rounded-lg bg-white/5 p-1">
      {options.map(opt => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          className={`relative px-3 py-1.5 text-xs rounded-md transition-colors ${
            theme === opt.value ? 'text-[#C8FF00]' : 'text-white/40 hover:text-white/60'
          }`}
        >
          {theme === opt.value && (
            <motion.div
              layoutId="theme-indicator"
              className="absolute inset-0 bg-white/10 rounded-md"
              transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
            />
          )}
          <span className="relative z-10">{opt.icon} {opt.label}</span>
        </button>
      ))}
    </div>
  );
}
