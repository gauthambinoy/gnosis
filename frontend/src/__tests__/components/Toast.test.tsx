import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ToastProvider, useToast } from "@/components/ui/Toast";

function Trigger() {
  const t = useToast();
  return (
    <div>
      <button onClick={() => t.success("Done", "It worked")}>fire</button>
      <button onClick={() => t.error("Oops")}>err</button>
    </div>
  );
}

describe("ui/Toast", () => {
  it("useToast outside provider throws", () => {
    expect(() => render(<Trigger />)).toThrow();
  });

  it("ToastProvider renders children", () => {
    render(
      <ToastProvider>
        <p>kids</p>
      </ToastProvider>,
    );
    expect(screen.getByText("kids")).toBeInTheDocument();
  });

  it("triggering success toast displays it", () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("fire"));
    expect(screen.getByText("Done")).toBeInTheDocument();
    expect(screen.getByText("It worked")).toBeInTheDocument();
  });
});
