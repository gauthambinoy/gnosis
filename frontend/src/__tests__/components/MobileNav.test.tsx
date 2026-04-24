import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

vi.mock("next/navigation", async () => {
  const m = await import("../test-utils");
  return m.nextNavigationMock;
});

import { MobileNav } from "@/components/ui/MobileNav";

describe("MobileNav", () => {
  beforeEach(() => {
    // jsdom default width is 1024 -> not mobile, returns null
    Object.defineProperty(window, "innerWidth", { value: 1024, configurable: true });
  });

  it("renders null on desktop without throwing", () => {
    const { container } = render(<MobileNav />);
    expect(container.firstChild).toBeNull();
  });

  it("renders toggle button on mobile widths", () => {
    Object.defineProperty(window, "innerWidth", { value: 500, configurable: true });
    const { container } = render(<MobileNav />);
    // toggle button has aria-label
    expect(container.querySelector('button[aria-label="Toggle navigation"]')).toBeTruthy();
  });
});
