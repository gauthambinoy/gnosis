"use client";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import clsx from "clsx";
import { MessageBubble, type Message } from "./MessageBubble";
import { AgentPreview, type AgentConfig } from "./AgentPreview";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "I'm the Gnosis Awakening. Describe what you need automated and I'll create an intelligent agent for you.\n\nFor example: \"Monitor my Gmail for invoices and log them to a Google Sheet with the amount, vendor, and due date.\"",
  timestamp: new Date(),
};

const SUGGESTED_PROMPTS = [
  "I waste hours on email",
  "Help me track invoices",
  "Automate my Slack standups",
];

interface ChatInterfaceProps {
  userName?: string;
}

// Try to parse an agent config from the accumulated assistant message
function tryParseAgentConfig(content: string): AgentConfig | null {
  // Look for JSON blocks fenced in ```json ... ``` or raw JSON with expected keys
  const jsonBlockMatch = content.match(/```json\s*([\s\S]*?)```/);
  const candidate = jsonBlockMatch ? jsonBlockMatch[1] : content;

  try {
    const parsed = JSON.parse(candidate.trim());
    if (parsed && typeof parsed.name === "string" && typeof parsed.description === "string") {
      return {
        name: parsed.name,
        description: parsed.description,
        emoji: parsed.emoji || "✦",
        triggers: Array.isArray(parsed.triggers) ? parsed.triggers : [],
        integrations: Array.isArray(parsed.integrations) ? parsed.integrations : [],
      };
    }
  } catch {
    // Not valid JSON — try to find embedded JSON object
    const braceMatch = content.match(/\{[\s\S]*"name"\s*:\s*"[^"]+[\s\S]*"description"\s*:\s*"[^"]+[\s\S]*\}/);
    if (braceMatch) {
      try {
        const parsed = JSON.parse(braceMatch[0]);
        if (parsed.name && parsed.description) {
          return {
            name: parsed.name,
            description: parsed.description,
            emoji: parsed.emoji || "✦",
            triggers: Array.isArray(parsed.triggers) ? parsed.triggers : [],
            integrations: Array.isArray(parsed.integrations) ? parsed.integrations : [],
          };
        }
      } catch {
        // ignore
      }
    }
  }
  return null;
}

export function ChatInterface({ userName = "U" }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);
  const [isAwakening, setIsAwakening] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        timestamp: new Date(),
      };

      const assistantId = `assistant-${Date.now()}`;
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);
      setAgentConfig(null);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${API_URL}/api/v1/awaken/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: trimmed }),
          signal: controller.signal,
        });

        if (!res.body) throw new Error("No response body");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullContent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;

            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "token") {
                fullContent += data.content;
                const captured = fullContent;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: captured } : m
                  )
                );
              }

              if (data.type === "agent_config" && data.config) {
                setAgentConfig(data.config as AgentConfig);
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }

        // After streaming completes, try to detect agent config from content
        if (!agentConfig) {
          const detected = tryParseAgentConfig(fullContent);
          if (detected) setAgentConfig(detected);
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    "I couldn't connect to the Gnosis backend. Make sure the server is running on port 8000.",
                }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, agentConfig]
  );

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleAwaken() {
    setIsAwakening(true);
    // Simulated — in production this would POST to the backend
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: `system-${Date.now()}`,
          role: "assistant",
          content: `✦ **${agentConfig?.name}** has been awakened and is now active. You can find it in your Nerve Center.`,
          timestamp: new Date(),
        },
      ]);
      setIsAwakening(false);
    }, 2000);
  }

  const showSuggestions = messages.length === 1 && !isStreaming;

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 scrollbar-thin">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isStreaming={
                isStreaming &&
                msg.role === "assistant" &&
                msg.id === messages[messages.length - 1]?.id
              }
              userName={userName}
            />
          ))}
        </AnimatePresence>

        {/* Typing indicator when streaming starts but no content yet */}
        <AnimatePresence>
          {isStreaming &&
            messages[messages.length - 1]?.role === "assistant" &&
            !messages[messages.length - 1]?.content && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 px-4 py-2 text-xs text-gnosis-muted"
              >
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-gnosis-gold/60 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-gnosis-gold/60 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-gnosis-gold/60 animate-bounce [animation-delay:300ms]" />
                </span>
                Gnosis is thinking…
              </motion.div>
            )}
        </AnimatePresence>

        {/* Agent Preview Card */}
        <AnimatePresence>
          {agentConfig && !isStreaming && (
            <AgentPreview
              config={agentConfig}
              onAwaken={handleAwaken}
              isAwakening={isAwakening}
            />
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested prompts */}
      <AnimatePresence>
        {showSuggestions && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="flex flex-wrap gap-2 pb-4"
          >
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => sendMessage(prompt)}
                className="px-4 py-2 rounded-xl border border-gnosis-border bg-gnosis-surface text-xs text-gnosis-text hover:border-gnosis-primary/40 hover:text-gnosis-primary transition-colors"
              >
                {prompt}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div className="border-t border-gnosis-border pt-4">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you need automated…"
            rows={1}
            className={clsx(
              "flex-1 bg-gnosis-surface border border-gnosis-border rounded-xl px-4 py-3",
              "text-sm text-gnosis-text placeholder:text-gnosis-muted/50",
              "focus:outline-none focus:border-gnosis-primary/50",
              "resize-none transition-colors"
            )}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isStreaming}
            className={clsx(
              "px-5 py-3 rounded-xl font-medium text-sm transition-all",
              "bg-gnosis-primary text-gnosis-bg",
              "hover:shadow-[0_0_30px_rgba(200,255,0,0.3)]",
              "disabled:opacity-30 disabled:hover:shadow-none"
            )}
          >
            {isStreaming ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 border-2 border-gnosis-bg/30 border-t-gnosis-bg rounded-full animate-spin" />
              </span>
            ) : (
              "Send"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
