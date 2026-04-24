import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { ExecutionHistory } from "@/components/mindseye/ExecutionHistory";

describe("ExecutionHistory", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({ executions: [] }) }) as Response),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders without crashing and fetches", async () => {
    const { container } = render(<ExecutionHistory agentId="a1" />);
    await waitFor(() => expect(container.firstChild).toBeTruthy());
    expect(globalThis.fetch).toHaveBeenCalled();
  });
});
