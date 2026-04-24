import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { resetRouterMocks } from "../test-utils";

vi.mock("next/navigation", async () => {
  const m = await import("../test-utils");
  return m.nextNavigationMock;
});

import { CommandPalette } from "@/components/ui/CommandPalette";

describe("CommandPalette", () => {
  beforeEach(() => resetRouterMocks());

  it("opens with cmd+k and shows commands", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByText(/Go to Dashboard/)).toBeInTheDocument();
  });

  it("filters commands by query", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const input = screen.getByPlaceholderText(/Type a command/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Pipelines" } });
    expect(screen.getByText(/Go to Pipelines/)).toBeInTheDocument();
    expect(screen.queryByText("Go to Dashboard")).toBeNull();
  });

  it("escape closes the palette", async () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByText(/Go to Dashboard/)).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByText("Go to Dashboard")).toBeNull());
  });
});
