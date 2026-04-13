"use client";

import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  userName?: string;
}

// Lightweight markdown renderer — handles bold, inline code, code blocks, and lists
function renderMarkdown(text: string) {
  const blocks = text.split(/```(\w*)\n?([\s\S]*?)```/g);
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < blocks.length; i++) {
    if (i % 3 === 0) {
      // Regular text block
      const lines = blocks[i].split("\n");
      const lineElements: React.ReactNode[] = [];

      for (let li = 0; li < lines.length; li++) {
        const line = lines[li];

        // Unordered list items
        if (/^[\s]*[-*]\s/.test(line)) {
          lineElements.push(
            <div key={`li-${li}`} className="flex gap-2 pl-2">
              <span className="text-gnosis-primary/60 select-none">•</span>
              <span>{renderInline(line.replace(/^[\s]*[-*]\s/, ""))}</span>
            </div>
          );
          continue;
        }

        // Ordered list items
        if (/^[\s]*\d+\.\s/.test(line)) {
          const num = line.match(/^[\s]*(\d+)\./)?.[1];
          lineElements.push(
            <div key={`li-${li}`} className="flex gap-2 pl-2">
              <span className="text-gnosis-muted select-none">{num}.</span>
              <span>{renderInline(line.replace(/^[\s]*\d+\.\s/, ""))}</span>
            </div>
          );
          continue;
        }

        if (li > 0) lineElements.push(<br key={`br-${li}`} />);
        lineElements.push(
          <span key={`t-${li}`}>{renderInline(line)}</span>
        );
      }

      elements.push(<span key={`block-${i}`}>{lineElements}</span>);
    } else if (i % 3 === 1) {
      // Code language tag — skip, handled with next block
      continue;
    } else {
      // Code block content
      const lang = blocks[i - 1];
      elements.push(
        <pre
          key={`code-${i}`}
          className="my-2 rounded-lg bg-gnosis-bg border border-gnosis-border px-4 py-3 overflow-x-auto text-xs font-mono"
        >
          {lang && (
            <span className="block text-[10px] text-gnosis-muted mb-1 uppercase tracking-wider">
              {lang}
            </span>
          )}
          <code>{blocks[i]}</code>
        </pre>
      );
    }
  }

  return elements;
}

function renderInline(text: string): React.ReactNode[] {
  // Bold, inline code
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-gnosis-text">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 rounded bg-gnosis-bg border border-gnosis-border text-gnosis-primary/80 text-xs font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function formatTime(date: Date) {
  return new Date(date).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function MessageBubbleComponent({
  message,
  isStreaming = false,
  userName = "U",
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const initial = userName.charAt(0).toUpperCase();

  const renderedContent = useMemo(
    () => (message.content ? renderMarkdown(message.content) : null),
    [message.content]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={clsx("flex gap-3 group", isUser ? "justify-end" : "justify-start")}
    >
      {/* Agent avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full border border-gnosis-gold/40 bg-gnosis-surface flex items-center justify-center text-sm text-gnosis-gold">
          ◎
        </div>
      )}

      <div className={clsx("max-w-[70%] flex flex-col", isUser ? "items-end" : "items-start")}>
        <div
          className={clsx(
            "rounded-2xl px-5 py-3 text-sm leading-relaxed",
            isUser
              ? "bg-gnosis-surface border border-gnosis-border text-gnosis-text"
              : "bg-gnosis-surface border border-gnosis-gold/20 text-gnosis-text"
          )}
        >
          <div className="whitespace-pre-wrap break-words">
            {renderedContent}
            {isStreaming && (
              <span
                className="inline-block w-[2px] h-[1em] bg-gnosis-primary ml-0.5 align-text-bottom animate-pulse"
                aria-hidden="true"
              />
            )}
            {!message.content && isStreaming && (
              <span className="inline-flex gap-1 items-center text-gnosis-muted text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-gnosis-primary/50 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-gnosis-primary/50 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-gnosis-primary/50 animate-bounce [animation-delay:300ms]" />
              </span>
            )}
          </div>
        </div>

        {/* Timestamp */}
        <span className="text-[10px] text-gnosis-muted mt-1 px-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full border border-gnosis-border bg-gnosis-surface flex items-center justify-center text-sm text-gnosis-text font-medium">
          {initial}
        </div>
      )}
    </motion.div>
  );
}

export const MessageBubble = memo(MessageBubbleComponent);
