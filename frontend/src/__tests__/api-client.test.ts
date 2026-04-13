import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const mockFetch = vi.fn();
global.fetch = mockFetch;

const initialState = useAuth.getState();

beforeEach(() => {
  vi.clearAllMocks();
  useAuth.setState({
    ...initialState,
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });
});

describe("api client", () => {
  it("authenticated requests include Authorization header", async () => {
    useAuth.setState({ accessToken: "my-token" });

    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await api.get("/test");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers).toHaveProperty("Authorization", "Bearer my-token");
  });

  it("401 triggers token refresh", async () => {
    useAuth.setState({
      accessToken: "expired",
      refreshToken: "ref-tok",
      isAuthenticated: true,
    });

    // First call returns 401
    mockFetch.mockResolvedValueOnce(new Response("{}", { status: 401 }));
    // Refresh call succeeds
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: "new-token" }), { status: 200 })
    );
    // Retry call succeeds
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ data: "ok" }), { status: 200 }));

    await api.get("/protected");

    // Should have made 3 fetch calls: original, refresh, retry
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("uses correct base URL", async () => {
    useAuth.setState({ accessToken: null });
    mockFetch.mockResolvedValueOnce(new Response("{}", { status: 200 }));

    await api.get("/agents");

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents");
  });
});
