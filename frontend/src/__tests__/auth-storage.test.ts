import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

const LEGACY_LS_KEY = "gnosis-auth";
const REFRESH_SS_KEY = "gnosis-auth-refresh";

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.resetModules();
});

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("token storage hardening (H11)", () => {
  it("login response never writes access or refresh tokens to localStorage", async () => {
    const { useAuth } = await import("@/lib/auth");

    const fakeLogin = {
      user: { id: "1", email: "a@b.com", full_name: "A" },
      access_token: "ACCESS-XYZ",
      refresh_token: "REFRESH-XYZ",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(fakeLogin), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await useAuth.getState().login("a@b.com", "pw");

    // Access token lives only in memory.
    expect(useAuth.getState().accessToken).toBe("ACCESS-XYZ");

    // Nothing about the access token may appear in localStorage.
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)!;
      const value = localStorage.getItem(key) ?? "";
      expect(value).not.toContain("ACCESS-XYZ");
      expect(value).not.toContain("REFRESH-XYZ");
    }
    expect(localStorage.getItem(LEGACY_LS_KEY)).toBeNull();
    expect(localStorage.length).toBe(0);

    // Refresh token is persisted, but only in sessionStorage.
    const ss = sessionStorage.getItem(REFRESH_SS_KEY);
    expect(ss).not.toBeNull();
    expect(ss!).toContain("REFRESH-XYZ");
  });

  it("refresh token is never written to localStorage on register", async () => {
    const { useAuth } = await import("@/lib/auth");

    const fakeReg = {
      user: { id: "2", email: "c@d.com", full_name: "C" },
      access_token: "AT2",
      refresh_token: "RT2",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(fakeReg), { status: 200 })),
    );

    await useAuth.getState().register("c@d.com", "pw", "C");

    expect(localStorage.getItem(LEGACY_LS_KEY)).toBeNull();
    for (let i = 0; i < localStorage.length; i++) {
      const v = localStorage.getItem(localStorage.key(i)!) ?? "";
      expect(v).not.toContain("RT2");
      expect(v).not.toContain("AT2");
    }
  });

  it("migrates legacy gnosis-auth localStorage entry to sessionStorage and deletes it", async () => {
    localStorage.setItem(
      LEGACY_LS_KEY,
      JSON.stringify({
        state: {
          user: { id: "1", email: "a@b.com", full_name: "A" },
          accessToken: "OLD-ACCESS",
          refreshToken: "OLD-REFRESH",
          isAuthenticated: true,
        },
        version: 0,
      }),
    );

    await import("@/lib/auth");

    expect(localStorage.getItem(LEGACY_LS_KEY)).toBeNull();
    expect(localStorage.length).toBe(0);

    const ss = sessionStorage.getItem(REFRESH_SS_KEY);
    expect(ss).not.toBeNull();
    expect(ss!).toContain("OLD-REFRESH");
    // Access token must NOT be migrated anywhere persistent.
    expect(ss!).not.toContain("OLD-ACCESS");
  });

  it("migration is a no-op when no legacy entry is present", async () => {
    await import("@/lib/auth");
    expect(localStorage.length).toBe(0);
  });

  it("corrupt legacy entry is deleted without throwing", async () => {
    localStorage.setItem(LEGACY_LS_KEY, "{not json");
    await expect(import("@/lib/auth")).resolves.toBeDefined();
    expect(localStorage.getItem(LEGACY_LS_KEY)).toBeNull();
  });
});
