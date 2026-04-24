import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble, type Message } from "@/components/awakening/MessageBubble";

const mkMsg = (overrides: Partial<Message> = {}): Message => ({
  id: "1",
  role: "user",
  content: "Hello world",
  timestamp: new Date("2024-01-01T00:00:00Z"),
  ...overrides,
});

describe("MessageBubble", () => {
  it("renders user message content", () => {
    render(<MessageBubble message={mkMsg()} />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("renders assistant message", () => {
    render(<MessageBubble message={mkMsg({ role: "assistant", content: "I am AI" })} />);
    expect(screen.getByText("I am AI")).toBeInTheDocument();
  });

  it("renders bullet list markdown", () => {
    const { container } = render(
      <MessageBubble message={mkMsg({ role: "assistant", content: "- alpha\n- beta" })} />,
    );
    expect(container.textContent).toContain("alpha");
    expect(container.textContent).toContain("beta");
  });

  it("isStreaming flag does not crash", () => {
    render(<MessageBubble message={mkMsg({ role: "assistant" })} isStreaming />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });
});
