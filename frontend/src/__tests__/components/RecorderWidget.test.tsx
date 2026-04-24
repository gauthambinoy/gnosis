import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RecorderWidget from "@/components/dashboard/RecorderWidget";

describe("RecorderWidget", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        ({ ok: true, json: async () => ({ session_id: "sess-1", count: 0 }) }) as Response,
      ),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders the start button initially", () => {
    render(<RecorderWidget />);
    // There's at least one button rendered
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });

  it("clicking start calls record/start endpoint", async () => {
    render(<RecorderWidget />);
    const btn = screen.getAllByRole("button")[0];
    fireEvent.click(btn);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/rpa/record/start"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});
