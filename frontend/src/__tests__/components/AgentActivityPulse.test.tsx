import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { installMockWebSocket, MockWebSocket } from "../test-utils";
import AgentActivityPulse from "@/components/dashboard/AgentActivityPulse";

describe("AgentActivityPulse", () => {
  beforeEach(() => installMockWebSocket());
  afterEach(() => vi.restoreAllMocks());

  it("renders nothing when no active agents", () => {
    const { container } = render(<AgentActivityPulse />);
    expect(container.textContent).toBe("");
  });

  it("renders agent dot when execution_phase event received", () => {
    render(<AgentActivityPulse wsUrl="ws://test" />);
    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.emit({
        type: "execution_phase",
        agent_id: "a1",
        phase: "perceive",
        timestamp: "2024-01-01T00:00:00Z",
        data: { status: "running" },
      });
    });
    expect(screen.getByText(/active/)).toBeInTheDocument();
  });
});
