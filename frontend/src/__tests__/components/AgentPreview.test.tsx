import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AgentPreview, type AgentConfig } from "@/components/awakening/AgentPreview";

const baseConfig: AgentConfig = {
  name: "Email Triage",
  description: "Sorts your inbox",
  emoji: "✉️",
  triggers: ["new email"],
  integrations: ["gmail", "slack"],
};

describe("AgentPreview", () => {
  it("renders name and description", () => {
    render(<AgentPreview config={baseConfig} onAwaken={() => {}} />);
    expect(screen.getByText("Email Triage")).toBeInTheDocument();
    expect(screen.getByText("Sorts your inbox")).toBeInTheDocument();
  });

  it("clicking awaken calls handler", () => {
    const onAwaken = vi.fn();
    render(<AgentPreview config={baseConfig} onAwaken={onAwaken} />);
    // Click any button — there should be an awaken CTA
    const buttons = screen.getAllByRole("button");
    // Find the primary CTA (last one is typically the awaken button)
    fireEvent.click(buttons[buttons.length - 1]);
    expect(onAwaken).toHaveBeenCalled();
  });

  it("renders integrations badges", () => {
    render(<AgentPreview config={baseConfig} onAwaken={() => {}} />);
    expect(screen.getByText("Gmail")).toBeInTheDocument();
    expect(screen.getByText("Slack")).toBeInTheDocument();
  });
});
