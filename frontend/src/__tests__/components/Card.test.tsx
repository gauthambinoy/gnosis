import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "@/components/shared/Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("merges className prop", () => {
    const { container } = render(<Card className="extra-class">Hello</Card>);
    expect(container.firstChild).toHaveClass("extra-class");
  });
});
