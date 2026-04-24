import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IntegrationCard, type Integration } from "@/components/integrations/IntegrationCard";

const base: Integration = {
  id: "gmail",
  name: "Gmail",
  icon: "✉️",
  description: "Email integration",
  status: "disconnected",
};

describe("IntegrationCard", () => {
  it("renders name and description", () => {
    render(<IntegrationCard integration={base} onConnect={() => {}} onDisconnect={() => {}} />);
    expect(screen.getByText("Gmail")).toBeInTheDocument();
    expect(screen.getByText("Email integration")).toBeInTheDocument();
  });

  it("connect action calls onConnect after delay", async () => {
    vi.useFakeTimers();
    const onConnect = vi.fn();
    render(<IntegrationCard integration={base} onConnect={onConnect} onDisconnect={() => {}} />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    await vi.advanceTimersByTimeAsync(1300);
    expect(onConnect).toHaveBeenCalledWith("gmail");
    vi.useRealTimers();
  });

  it("disconnect action calls onDisconnect when connected", async () => {
    vi.useFakeTimers();
    const onDisconnect = vi.fn();
    render(
      <IntegrationCard
        integration={{ ...base, status: "connected" }}
        onConnect={() => {}}
        onDisconnect={onDisconnect}
      />,
    );
    fireEvent.click(screen.getAllByRole("button")[0]);
    await vi.advanceTimersByTimeAsync(1300);
    expect(onDisconnect).toHaveBeenCalledWith("gmail");
    vi.useRealTimers();
  });
});
