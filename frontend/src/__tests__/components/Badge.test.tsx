import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/shared/Badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>hello</Badge>);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });
  it("applies variant class for success", () => {
    render(<Badge variant="success">ok</Badge>);
    const el = screen.getByText("ok");
    expect(el.className).toMatch(/success/);
  });
  it("applies variant class for error", () => {
    render(<Badge variant="error">bad</Badge>);
    expect(screen.getByText("bad").className).toMatch(/error/);
  });
  it("merges custom className", () => {
    render(<Badge className="custom-x">tag</Badge>);
    expect(screen.getByText("tag").className).toContain("custom-x");
  });
});
