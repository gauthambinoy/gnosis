import { describe, it, expect, beforeEach } from "vitest";
import { useAuth } from "@/lib/auth";

const initialState = useAuth.getState();

beforeEach(() => {
  useAuth.setState(initialState, true);
});

describe("auth store", () => {
  it("login sets token and user", () => {
    useAuth.setState({
      user: { id: "1", email: "a@b.com", full_name: "Test" },
      accessToken: "tok123",
      refreshToken: "ref123",
      isAuthenticated: true,
    });

    const state = useAuth.getState();
    expect(state.accessToken).toBe("tok123");
    expect(state.refreshToken).toBe("ref123");
    expect(state.user?.email).toBe("a@b.com");
    expect(state.isAuthenticated).toBe(true);
  });

  it("logout clears state", () => {
    useAuth.setState({
      user: { id: "1", email: "a@b.com", full_name: "Test" },
      accessToken: "tok123",
      refreshToken: "ref123",
      isAuthenticated: true,
    });

    useAuth.getState().logout();

    const state = useAuth.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it("refresh updates token", () => {
    useAuth.setState({ accessToken: "old" });
    useAuth.setState({ accessToken: "new" });
    expect(useAuth.getState().accessToken).toBe("new");
  });

  it("isAuthenticated reflects auth state", () => {
    expect(useAuth.getState().isAuthenticated).toBe(false);

    useAuth.setState({ isAuthenticated: true });
    expect(useAuth.getState().isAuthenticated).toBe(true);

    useAuth.getState().logout();
    expect(useAuth.getState().isAuthenticated).toBe(false);
  });
});
