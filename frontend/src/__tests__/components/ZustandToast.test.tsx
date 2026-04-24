import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { ToastContainer } from "@/components/ui/zustand-toast";
import { useToastStore } from "@/stores/toastStore";

describe("zustand-toast ToastContainer", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("renders no toasts initially", () => {
    const { container } = render(<ToastContainer />);
    // Wrapper exists but contains no toast items
    expect(container.querySelectorAll("[class*='border']").length).toBe(0);
  });

  it("displays a toast added to the store", () => {
    render(<ToastContainer />);
    act(() => {
      useToastStore.getState().addToast({ type: "success", title: "Hi", message: "world" });
    });
    expect(screen.getByText("Hi")).toBeInTheDocument();
    expect(screen.getByText("world")).toBeInTheDocument();
  });

  it("removes toast on click", () => {
    render(<ToastContainer />);
    act(() => {
      useToastStore.getState().addToast({ type: "info", title: "Bye" });
    });
    fireEvent.click(screen.getByText("Bye").closest("div")!);
    // After click, toast removed from store
    expect(useToastStore.getState().toasts.length).toBe(0);
  });
});
