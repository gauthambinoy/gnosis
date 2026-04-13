import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "@/components/shared/Button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("fires click handler", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Press</Button>);
    fireEvent.click(screen.getByText("Press"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("respects disabled state", () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Nope</Button>);
    const btn = screen.getByText("Nope");
    expect(btn).toBeDisabled();
  });

  it("applies variant classes", () => {
    render(<Button variant="secondary">Styled</Button>);
    const btn = screen.getByText("Styled");
    expect(btn.className).toContain("border");
  });
});
