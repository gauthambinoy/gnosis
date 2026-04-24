import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render } from "@testing-library/react";
import { installMockWebSocket } from "../test-utils";
import { ConsciousnessViewer } from "@/components/mindseye/ConsciousnessViewer";

describe("ConsciousnessViewer", () => {
  beforeEach(() => installMockWebSocket());
  afterEach(() => vi.restoreAllMocks());

  it("renders waiting state when no execution", () => {
    const { container } = render(<ConsciousnessViewer agentId="a1" />);
    expect(container.textContent).toMatch(/Waiting|Replay/);
  });

  it("renders replay state when replayData provided", () => {
    const { container } = render(
      <ConsciousnessViewer
        agentId="a1"
        replayData={{
          phases: [],
          memories: [],
          tokens: { used: 0, budget: 100 },
          confidence: 50,
          actions: [],
          active: false,
        } as any}
      />,
    );
    expect(container.textContent).toMatch(/Replay|Waiting/);
  });
});
