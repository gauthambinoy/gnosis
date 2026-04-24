import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import MemoryExplorer from "@/components/memory/MemoryExplorer";

describe("MemoryExplorer", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/stats")) {
          return { ok: true, json: async () => ({ total: 0, by_tier: {} }) } as Response;
        }
        return { ok: true, json: async () => ({ memories: [] }) } as Response;
      }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders without crashing", async () => {
    const { container } = render(<MemoryExplorer agentId="agent-1" />);
    await waitFor(() => expect(container.firstChild).toBeTruthy());
  });

  it("calls memory API endpoints", async () => {
    render(<MemoryExplorer agentId="agent-1" />);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
  });
});
