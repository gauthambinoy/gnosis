"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AwakenPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "I'm the Gnosis Awakening. Describe what you need automated and I'll create an intelligent agent for you.\n\nFor example: \"Monitor my Gmail for invoices and log them to a Google Sheet with the amount, vendor, and due date.\"",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    const assistantId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", timestamp: new Date() },
    ]);

    try {
      const res = await fetch(
        API_URL + "/api/v1/awaken/chat",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMsg.content }),
        }
      );

      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === "token") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: m.content + data.content } : m
                  )
                );
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "I couldn't connect to the Gnosis backend. Make sure the server is running on port 8000." }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold text-gnosis-text">✦ The Awakening</h1>
        <p className="text-gnosis-muted mt-1">Describe what you need. I&apos;ll create an agent for you.</p>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pb-4 scrollbar-thin">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={"flex " + (msg.role === "user" ? "justify-end" : "justify-start")}
            >
              <div
                className={"max-w-[70%] rounded-2xl px-5 py-3 " + (
                  msg.role === "user"
                    ? "bg-gnosis-primary/10 text-gnosis-primary border border-gnosis-primary/20"
                    : "bg-gnosis-surface border border-gnosis-border text-gnosis-text"
                )}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                {msg.role === "assistant" && isStreaming && msg === messages[messages.length - 1] && (
                  <span className="inline-block w-2 h-4 bg-gnosis-primary/60 animate-pulse ml-0.5" />
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gnosis-border pt-4">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you need automated..."
            rows={1}
            className="flex-1 bg-gnosis-surface border border-gnosis-border rounded-xl px-4 py-3 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50 resize-none transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="px-5 py-3 rounded-xl bg-gnosis-primary text-gnosis-bg font-medium text-sm hover:shadow-[0_0_30px_rgba(200,255,0,0.3)] disabled:opacity-30 disabled:hover:shadow-none transition-all"
          >
            {isStreaming ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
