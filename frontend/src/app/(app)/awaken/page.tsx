"use client";

import { ChatInterface } from "@/components/awakening/ChatInterface";

export default function AwakenPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold text-gnosis-text">
          ✦ The Awakening
        </h1>
        <p className="text-gnosis-muted mt-1">
          Describe what you need. I&apos;ll create an agent for you.
        </p>
      </div>

      <ChatInterface />
    </div>
  );
}
