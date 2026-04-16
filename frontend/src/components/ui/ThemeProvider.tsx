"use client";
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

type Theme = "dark" | "light" | "system";
interface ThemeContextType { theme: Theme; resolvedTheme: "dark" | "light"; setTheme: (theme: Theme) => void; toggleTheme: () => void; }
const ThemeContext = createContext<ThemeContextType>({ theme: "dark", resolvedTheme: "dark", setTheme: () => {}, toggleTheme: () => {} });
export function useTheme() { return useContext(ThemeContext); }

function getSystemTheme(): "dark" | "light" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [resolvedTheme, setResolvedTheme] = useState<"dark" | "light">("dark");

  useEffect(() => { const saved = localStorage.getItem("gnosis-theme") as Theme | null; if (saved && ["dark", "light", "system"].includes(saved)) setThemeState(saved); }, []);
  useEffect(() => { const resolved = theme === "system" ? getSystemTheme() : theme; setResolvedTheme(resolved); document.documentElement.classList.remove("dark", "light"); document.documentElement.classList.add(resolved); document.documentElement.setAttribute("data-theme", resolved); }, [theme]);
  useEffect(() => { if (theme !== "system") return; const mq = window.matchMedia("(prefers-color-scheme: dark)"); const handler = () => setResolvedTheme(mq.matches ? "dark" : "light"); mq.addEventListener("change", handler); return () => mq.removeEventListener("change", handler); }, [theme]);

  const setTheme = useCallback((t: Theme) => { setThemeState(t); localStorage.setItem("gnosis-theme", t); }, []);
  const toggleTheme = useCallback(() => { setTheme(resolvedTheme === "dark" ? "light" : "dark"); }, [resolvedTheme, setTheme]);

  return <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function ThemeToggle() {
  const { resolvedTheme, toggleTheme } = useTheme();
  return (
    <button onClick={toggleTheme} className="w-9 h-9 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/10 flex items-center justify-center transition-colors" aria-label="Toggle theme" title={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`}>
      {resolvedTheme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
