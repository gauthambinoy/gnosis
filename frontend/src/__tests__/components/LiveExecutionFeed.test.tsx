import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { installMockWebSocket, MockWebSocket } from "../test-utils";
import LiveExecutionFeed from "@/components/dashboard/LiveExecutionFeed";

describe("LiveExecutionFeed", () => {
  beforeEach(() => installMockWebSocket());
  afterEach(() => vi.restoreAllMocks());

  it("renders without throwing and creates a websocket", () => {
    render(<LiveExecutionFeed />);
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
  });

  it("appends events emitted by the websocket", async () => {
    const { container } = render(<LiveExecutionFeed />);
    const ws = MockWebSocket.instances[0];
    await act(async () => {
      ws.emit({
        type: "execution_phase",
        agent_id: "alpha",
        phase: "act",
        data: { status: "completed", duration_ms: 12 },
        timestamp: "2024-01-01T00:00:00Z",
      });
    });
    expect(container.textContent).toContain("alpha");
  });
});
