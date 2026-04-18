import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Skeleton,
  AgentCardSkeleton,
  TableSkeleton,
} from "@/components/ui/skeleton";

describe("Skeleton primitives", () => {
  it("renders Skeleton with merged className", () => {
    const { container } = render(<Skeleton className="h-10 w-10" />);
    const el = container.firstChild as HTMLElement;
    expect(el).toHaveClass("animate-pulse");
    expect(el).toHaveClass("h-10");
    expect(el).toHaveClass("w-10");
  });

  it("renders AgentCardSkeleton without crashing", () => {
    const { container } = render(<AgentCardSkeleton />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(
      0,
    );
  });

  it("TableSkeleton renders the requested number of rows", () => {
    const { container } = render(<TableSkeleton rows={3} />);
    // Each row has 4 columns + the header has 0 in this component, so total
    // Skeleton elements should be rows * 4.
    const pulses = container.querySelectorAll(".animate-pulse");
    expect(pulses.length).toBe(3 * 4);
  });

  it("TableSkeleton defaults to 5 rows", () => {
    const { container } = render(<TableSkeleton />);
    const pulses = container.querySelectorAll(".animate-pulse");
    expect(pulses.length).toBe(5 * 4);
  });
});
