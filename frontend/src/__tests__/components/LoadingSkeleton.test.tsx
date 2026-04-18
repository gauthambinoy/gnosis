import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import {
  CardSkeleton,
  TableSkeleton,
} from "@/components/ui/LoadingSkeleton";

describe("LoadingSkeleton", () => {
  it("CardSkeleton renders a known number of pulse blocks", () => {
    const { container } = render(<CardSkeleton />);
    // 3 text bars + 2 button pills = 5 framer Pulse divs.
    const pulses = container.querySelectorAll("div.bg-white\\/\\[0\\.06\\]");
    expect(pulses.length).toBe(5);
  });

  it("TableSkeleton honours the rows prop", () => {
    const { container } = render(<TableSkeleton rows={4} />);
    // Header row has 4 cells + each data row has 4 cells = (1 + rows) * 4
    const pulses = container.querySelectorAll("div.bg-white\\/\\[0\\.06\\]");
    expect(pulses.length).toBe((1 + 4) * 4);
  });

  it("TableSkeleton defaults to 5 data rows", () => {
    const { container } = render(<TableSkeleton />);
    const pulses = container.querySelectorAll("div.bg-white\\/\\[0\\.06\\]");
    expect(pulses.length).toBe((1 + 5) * 4);
  });
});
