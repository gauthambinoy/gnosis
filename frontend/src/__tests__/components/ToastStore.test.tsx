import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { useToastStore } from "@/stores/toastStore";
import { ToastContainer } from "@/components/ui/zustand-toast";

describe("toastStore + ToastContainer", () => {
  beforeEach(() => {
    // Reset store between tests.
    useToastStore.setState({ toasts: [] });
    vi.useFakeTimers();
  });

  it("addToast pushes a toast with a generated id", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "success", title: "Saved" });
    });
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0].title).toBe("Saved");
    expect(toasts[0].type).toBe("success");
    expect(toasts[0].id).toMatch(/^[a-z0-9]+$/);
  });

  it("auto-removes a toast after the default 4s duration", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "info", title: "FYI" });
    });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("removeToast strips the matching toast immediately", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "error", title: "Boom" });
    });
    const id = useToastStore.getState().toasts[0].id;
    act(() => {
      useToastStore.getState().removeToast(id);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("ToastContainer renders the active toasts", () => {
    act(() => {
      useToastStore.getState().addToast({
        type: "warning",
        title: "Heads up",
        message: "be careful",
      });
    });
    render(<ToastContainer />);
    expect(screen.getByText("Heads up")).toBeInTheDocument();
    expect(screen.getByText("be careful")).toBeInTheDocument();
  });
});
