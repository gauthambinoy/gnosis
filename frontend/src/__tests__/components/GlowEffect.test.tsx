import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { GlowEffect } from "@/components/shared/GlowEffect";

describe("GlowEffect", () => {
  it("renders children", () => {
    render(<GlowEffect><span>inner</span></GlowEffect>);
    expect(screen.getByText("inner")).toBeInTheDocument();
  });
  it("applies custom className", () => {
    const { container } = render(
      <GlowEffect className="my-glow"><span>x</span></GlowEffect>,
    );
    expect(container.querySelector(".my-glow")).toBeTruthy();
  });
});
