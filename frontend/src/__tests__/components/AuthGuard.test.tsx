import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { useAuth } from "@/lib/auth";

// Mock next/navigation
const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { AuthGuard } from "@/components/auth/AuthGuard";

const initialState = useAuth.getState();

beforeEach(() => {
  vi.clearAllMocks();
  useAuth.setState(initialState, true);
});

describe("AuthGuard", () => {
  it("redirects when not authenticated", () => {
    useAuth.setState({ isAuthenticated: false, isLoading: false });

    render(
      <AuthGuard>
        <div>Protected</div>
      </AuthGuard>
    );

    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
    expect(pushMock).toHaveBeenCalledWith("/login");
  });

  it("renders children when authenticated", () => {
    useAuth.setState({ isAuthenticated: true, isLoading: false });

    render(
      <AuthGuard>
        <div>Protected</div>
      </AuthGuard>
    );

    expect(screen.getByText("Protected")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
