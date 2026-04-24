import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ThemeToggle from "@/components/ui/ThemeToggle";
import { ThemeProvider } from "@/lib/theme";

describe("ThemeToggle", () => {
  it("renders all three options", () => {
    render(<ThemeProvider><ThemeToggle /></ThemeProvider>);
    expect(screen.getByText(/Dark/)).toBeInTheDocument();
    expect(screen.getByText(/Light/)).toBeInTheDocument();
    expect(screen.getByText(/System/)).toBeInTheDocument();
  });

  it("clicking light persists to localStorage", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    render(<ThemeProvider><ThemeToggle /></ThemeProvider>);
    fireEvent.click(screen.getByText(/Light/));
    expect(setItem).toHaveBeenCalledWith("gnosis-theme", "light");
    setItem.mockRestore();
  });
});
