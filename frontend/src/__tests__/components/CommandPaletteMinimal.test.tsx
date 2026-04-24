import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { resetRouterMocks } from "../test-utils";

vi.mock("next/navigation", async () => {
  const m = await import("../test-utils");
  return m.nextNavigationMock;
});

import { CommandPaletteMinimal } from "@/components/ui/command-palette";

describe("command-palette (minimal)", () => {
  beforeEach(() => resetRouterMocks());

  it("renders nothing initially", () => {
    const { container } = render(<CommandPaletteMinimal />);
    // AnimatePresence empty
    expect(container.querySelector("input")).toBeNull();
  });

  it("opens with cmd+k", () => {
    render(<CommandPaletteMinimal />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByText(/Go to Agents/)).toBeInTheDocument();
  });
});
