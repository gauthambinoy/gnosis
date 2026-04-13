export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-gnosis-border bg-gnosis-surface p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="font-display text-2xl font-bold text-gnosis-primary">◎ Gnosis</h1>
        </div>
        <nav className="flex-1 space-y-1">
          {[
            { name: "Nerve Center", href: "/nerve-center", icon: "◉" },
            { name: "Awaken Agent", href: "/awaken", icon: "✦" },
            { name: "Oracle", href: "/oracle", icon: "🔮" },
            { name: "Standup", href: "/standup", icon: "📋" },
            { name: "Settings", href: "/settings", icon: "⚙" },
          ].map((item) => (
            <a
              key={item.name}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-gnosis-muted hover:text-gnosis-text hover:bg-gnosis-bg transition-colors"
            >
              <span>{item.icon}</span>
              <span>{item.name}</span>
            </a>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
