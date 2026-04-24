import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Skeleton, AgentCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";

describe("ui/skeleton", () => {
  it("renders Skeleton with default styles", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toBeTruthy();
    expect((container.firstChild as HTMLElement).className).toMatch(/animate-pulse/);
  });
  it("Skeleton merges className", () => {
    const { container } = render(<Skeleton className="h-10" />);
    expect((container.firstChild as HTMLElement).className).toContain("h-10");
  });
  it("renders AgentCardSkeleton", () => {
    const { container } = render(<AgentCardSkeleton />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(2);
  });
  it("TableSkeleton renders configurable rows", () => {
    const { container } = render(<TableSkeleton rows={3} />);
    // 3 rows * 4 skeletons each = 12
    expect(container.querySelectorAll(".animate-pulse").length).toBe(12);
  });
  it("TableSkeleton default rows = 5", () => {
    const { container } = render(<TableSkeleton />);
    expect(container.querySelectorAll(".animate-pulse").length).toBe(20);
  });
});
