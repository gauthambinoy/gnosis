"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", icon: "🏠", label: "Home" },
  { href: "/awaken", icon: "🤖", label: "Agents" },
  { href: "/pipelines", icon: "🔗", label: "Pipelines" },
  { href: "/knowledge", icon: "📚", label: "Knowledge" },
  { href: "/oracle", icon: "🔮", label: "Oracle" },
  { href: "/factory", icon: "🏭", label: "Factory" },
  { href: "/swarm", icon: "🐝", label: "Swarm" },
  { href: "/marketplace", icon: "🏪", label: "Market" },
  { href: "/dreams", icon: "💭", label: "Dreams" },
  { href: "/replay", icon: "⏪", label: "Replay" },
  { href: "/security", icon: "🛡️", label: "Security" },
  { href: "/billing", icon: "💳", label: "Billing" },
  { href: "/settings", icon: "⚙️", label: "Settings" },
  { href: "/system", icon: "🖥️", label: "System" },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => { setIsOpen(false); }, [pathname]);

  if (!isMobile) return null;

  return (
    <>
      <button onClick={() => setIsOpen(!isOpen)} className="fixed top-4 left-4 z-[9997] md:hidden w-10 h-10 rounded-xl bg-white/[0.06] border border-white/10 flex items-center justify-center backdrop-blur-md" aria-label="Toggle navigation">
        <motion.span animate={isOpen ? { rotate: 90 } : { rotate: 0 }} className="text-lg">{isOpen ? "✕" : "☰"}</motion.span>
      </button>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[9995] bg-black/60 backdrop-blur-sm md:hidden" onClick={() => setIsOpen(false)} />
            <motion.nav initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ type: "spring", damping: 25, stiffness: 300 }} className="fixed top-0 left-0 bottom-0 z-[9996] w-72 bg-[#0d1117] border-r border-white/10 overflow-y-auto md:hidden">
              <div className="p-4 pt-16">
                <div className="flex items-center gap-2 mb-6 px-2">
                  <span className="text-2xl">🧠</span>
                  <span className="text-lg font-bold text-white">Gnosis</span>
                </div>
                <div className="space-y-1">
                  {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                    return (
                      <Link key={item.href} href={item.href} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20" : "text-white/50 hover:text-white/80 hover:bg-white/[0.04]"}`}>
                        <span className="text-base w-6 text-center">{item.icon}</span>
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            </motion.nav>
          </>
        )}
      </AnimatePresence>
      <nav className="fixed bottom-0 left-0 right-0 z-[9994] md:hidden bg-[#0d1117]/95 backdrop-blur-md border-t border-white/[0.06]">
        <div className="flex items-center justify-around py-2 px-1">
          {NAV_ITEMS.slice(0, 5).map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} className={`flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg min-w-[3.5rem] ${isActive ? "text-cyan-400" : "text-white/40"}`}>
                <span className="text-lg">{item.icon}</span>
                <span className="text-[10px] font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
