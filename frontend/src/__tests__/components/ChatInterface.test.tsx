import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { ChatInterface } from "@/components/awakening/ChatInterface";

describe("ChatInterface", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({}) }) as Response),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders the welcome message", () => {
    const { container } = render(<ChatInterface userName="Alice" />);
    expect(container.textContent).toMatch(/Gnosis Awakening/);
  });

  it("shows suggested prompts", () => {
    const { container } = render(<ChatInterface />);
    expect(container.textContent).toContain("waste hours on email");
  });
});
