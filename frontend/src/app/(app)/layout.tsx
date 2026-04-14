"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore } from "@/lib/store";
import { useAuth } from "@/lib/auth";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { clsx } from "clsx";

const NAV_ITEMS = [
  { name: "Nerve Center", href: "/nerve-center", icon: "◉", description: "Dashboard" },
  { name: "✨ Factory", href: "/factory", icon: "✨", description: "Create agents from text" },
  { name: "Awaken", href: "/awaken", icon: "✦", description: "Create agents" },
  { name: "Schedules", href: "/schedules", icon: "🕐", description: "Agent scheduling" },
  { name: "Oracle", href: "/oracle", icon: "⟐", description: "Insights" },
  { name: "Forge", href: "/integrations", icon: "🧩", description: "Integrations" },
  { name: "Pipelines", href: "/pipelines", icon: "⟟", description: "Multi-agent pipelines" },
  { name: "Templates", href: "/templates", icon: "📋", description: "Workflow templates" },
  { name: "Marketplace", href: "/marketplace", icon: "🏪", description: "Agent marketplace" },
  { name: "Documents", href: "/documents", icon: "📄", description: "RAG documents" },
  { name: "Collaboration", href: "/collaboration", icon: "🤝", description: "Agent rooms" },
  { name: "Knowledge", href: "/knowledge", icon: "🧠", description: "Knowledge graph" },
  { name: "Swarm", href: "/swarm", icon: "🐝", description: "Agent swarm intelligence" },
  { name: "APIs", href: "/api-hub", icon: "🔗", description: "Auto-API discovery" },
  { name: "Automations", href: "/automations", icon: "🤖", description: "Browser RPA" },
  { name: "Dreams", href: "/dreams", icon: "🌀", description: "Agent dreams & evolution" },
  { name: "Predictions", href: "/predictions", icon: "🔮", description: "Predictive agents" },
  { name: "Real World", href: "/realworld", icon: "🌍", description: "Real-world connectors" },
  { name: "System", href: "/system", icon: "🖥️", description: "System control" },
  { name: "Standup", href: "/standup", icon: "◈", description: "Daily report" },
  { name: "Replay", href: "/replay", icon: "▶", description: "Execution replay" },
  { name: "Billing", href: "/billing", icon: "💳", description: "Plans & usage" },
  { name: "Infrastructure", href: "/infrastructure", icon: "🏗️", description: "System status" },
  { name: "Security", href: "/security", icon: "🛡️", description: "Security center" },
  { name: "Settings", href: "/settings", icon: "⚙", description: "Configuration" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { sidebarOpen, toggleSidebar } = useAppStore();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia("(max-width: 767px)");
    const onChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(e.matches);
      if (!e.matches) setMobileMenuOpen(false);
    };
    onChange(mql);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const userInitial = user?.full_name?.charAt(0).toUpperCase() || "?";

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        {/* Mobile hamburger button */}
        {isMobile && (
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="mobile-only fixed top-4 left-4 z-30 w-10 h-10 flex items-center justify-center rounded-xl bg-gnosis-surface border border-gnosis-border text-gnosis-text hover:text-gnosis-primary transition-colors"
            aria-label="Open menu"
          >
            <span className="text-xl">☰</span>
          </button>
        )}

        {/* Mobile overlay */}
        <AnimatePresence>
          {isMobile && mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mobile-overlay"
              onClick={() => setMobileMenuOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* Mobile sidebar */}
        {isMobile && (
          <aside className={clsx("mobile-sidebar bg-gnosis-surface border-r border-gnosis-border flex flex-col", mobileMenuOpen && "open")}>
            {/* Logo */}
            <div className="flex items-center gap-3 px-5 h-16 border-b border-gnosis-border shrink-0">
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="text-gnosis-primary text-2xl font-bold hover:scale-110 transition-transform"
              >
                ◎
              </button>
              <span className="font-display text-xl font-bold text-gnosis-primary whitespace-nowrap">
                GNOSIS
              </span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 space-y-1">
              {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)}>
                    <div
                      className={clsx(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative",
                        isActive
                          ? "bg-gnosis-primary/10 text-gnosis-primary"
                          : "text-gnosis-muted hover:text-gnosis-text hover:bg-white/[0.03]"
                      )}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="nav-indicator-mobile"
                          className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-gnosis-primary rounded-full"
                          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                        />
                      )}
                      <span className="text-lg shrink-0">{item.icon}</span>
                      <span className="text-sm font-medium truncate">{item.name}</span>
                    </div>
                  </Link>
                );
              })}
            </nav>

            {/* User section */}
            <div className="border-t border-gnosis-border p-3 shrink-0">
              <div className="flex items-center gap-3 px-3 py-2">
                <div className="w-8 h-8 rounded-full bg-gnosis-primary/20 flex items-center justify-center text-gnosis-primary text-sm font-bold shrink-0">
                  {userInitial}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gnosis-text truncate">
                    {user?.full_name || "User"}
                  </p>
                  <p className="text-xs text-gnosis-muted truncate">
                    {user?.email || ""}
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 px-3 py-2 rounded-xl text-gnosis-muted hover:text-red-400 hover:bg-red-400/5 transition-all duration-200 w-full mt-1"
              >
                <span className="text-lg shrink-0">⏻</span>
                <span className="text-sm">Sign Out</span>
              </button>
            </div>
          </aside>
        )}

        {/* Desktop sidebar */}
        {!isMobile && (
          <motion.aside
            initial={false}
            animate={{ width: sidebarOpen ? 256 : 72 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            className="desktop-only fixed left-0 top-0 h-screen border-r border-gnosis-border bg-gnosis-surface flex flex-col z-40 overflow-hidden"
          >
            {/* Logo */}
            <div className="flex items-center gap-3 px-5 h-16 border-b border-gnosis-border shrink-0">
              <button onClick={toggleSidebar} className="text-gnosis-primary text-2xl font-bold hover:scale-110 transition-transform">
                ◎
              </button>
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="font-display text-xl font-bold text-gnosis-primary whitespace-nowrap"
                  >
                    GNOSIS
                  </motion.span>
                )}
              </AnimatePresence>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 space-y-1">
              {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link key={item.href} href={item.href}>
                    <div
                      className={clsx(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative",
                        isActive
                          ? "bg-gnosis-primary/10 text-gnosis-primary"
                          : "text-gnosis-muted hover:text-gnosis-text hover:bg-white/[0.03]"
                      )}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="nav-indicator"
                          className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-gnosis-primary rounded-full"
                          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                        />
                      )}
                      <span className="text-lg shrink-0">{item.icon}</span>
                      <AnimatePresence>
                        {sidebarOpen && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col min-w-0"
                          >
                            <span className="text-sm font-medium truncate">{item.name}</span>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </Link>
                );
              })}
            </nav>

            {/* User section */}
            <div className="border-t border-gnosis-border p-3 shrink-0">
              <div className="flex items-center gap-3 px-3 py-2">
                <div className="w-8 h-8 rounded-full bg-gnosis-primary/20 flex items-center justify-center text-gnosis-primary text-sm font-bold shrink-0">
                  {userInitial}
                </div>
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="min-w-0 flex-1"
                    >
                      <p className="text-sm font-medium text-gnosis-text truncate">
                        {user?.full_name || "User"}
                      </p>
                      <p className="text-xs text-gnosis-muted truncate">
                        {user?.email || ""}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <button
                onClick={handleLogout}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-xl text-gnosis-muted hover:text-red-400 hover:bg-red-400/5 transition-all duration-200 w-full mt-1",
                  !sidebarOpen && "justify-center"
                )}
              >
                <span className="text-lg shrink-0">⏻</span>
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-sm"
                    >
                      Sign Out
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>
          </motion.aside>
        )}

        {/* Main content */}
        <motion.main
          initial={false}
          animate={{ marginLeft: isMobile ? 0 : (sidebarOpen ? 256 : 72) }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          className="flex-1 min-h-screen"
        >
          <div className={clsx("max-w-7xl mx-auto", isMobile ? "p-4 pt-16" : "p-8")}>
            {children}
          </div>
        </motion.main>
      </div>
    </AuthGuard>
  );
}
