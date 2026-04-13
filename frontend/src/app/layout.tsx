import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gnosis — The Knowledge That Works",
  description: "AI agents that think, learn, and work. Build intelligent automations by simply describing what you need.",
  openGraph: {
    title: "Gnosis — The Knowledge That Works",
    description: "AI agents that think, learn, and work.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-gnosis-bg text-gnosis-text font-body antialiased">
        {children}
      </body>
    </html>
  );
}
