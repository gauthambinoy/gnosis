/*
 * Token storage hardening (issue H11).
 *
 * Previous behavior: both accessToken and refreshToken were persisted to
 * localStorage via Zustand's `persist` middleware (key: "gnosis-auth").
 * That made both tokens trivially exfiltrable by any successful XSS.
 *
 * Current (interim) model:
 *   - accessToken: kept IN MEMORY ONLY on the Zustand store. Never written to
 *     localStorage or sessionStorage. Lost on full page reload — the
 *     refreshToken is used to mint a new one.
 *   - refreshToken: persisted to sessionStorage under key
 *     "gnosis-auth-refresh". Cleared automatically when the tab closes,
 *     and never written to localStorage.
 *   - On first load, any legacy "gnosis-auth" entry in localStorage is
 *     migrated (refreshToken extracted into sessionStorage) and DELETED.
 *
 * TODO follow-up: the backend should issue the refresh token as an
 * httpOnly + SameSite=Strict + Secure cookie scoped to the auth refresh
 * endpoint, eliminating JS access entirely. This file is the interim
 * hardening to remove the localStorage exposure now; the cookie-based
 * design will replace sessionStorage once the backend lands.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

const LEGACY_LS_KEY = "gnosis-auth";
const REFRESH_SS_KEY = "gnosis-auth-refresh";

// Run once, synchronously, before the store is created.
function migrateLegacyTokenStorage(): string | null {
  if (typeof window === "undefined") return null;
  let migratedRefresh: string | null = null;
  try {
    const raw = window.localStorage.getItem(LEGACY_LS_KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        const refresh: unknown = parsed?.state?.refreshToken ?? parsed?.refreshToken;
        if (typeof refresh === "string" && refresh.length > 0) {
          migratedRefresh = refresh;
          window.sessionStorage.setItem(
            REFRESH_SS_KEY,
            JSON.stringify({ state: { refreshToken: refresh }, version: 0 }),
          );
        }
      } catch {
        // Corrupt legacy payload — drop it anyway.
      }
      window.localStorage.removeItem(LEGACY_LS_KEY);
    }
  } catch {
    // localStorage / sessionStorage may be unavailable (e.g. privacy mode).
  }
  return migratedRefresh;
}

migrateLegacyTokenStorage();

interface User {
  id: string;
  email: string;
  full_name: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  setLoading: (loading: boolean) => void;
}

const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,

      login: async (email, password) => {
        const res = await fetch(`${API}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!res.ok)
          throw new Error((await res.json()).detail || "Login failed");
        const data = await res.json();
        set({
          user: data.user,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          isAuthenticated: true,
        });
      },

      register: async (email, password, fullName) => {
        const res = await fetch(`${API}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, full_name: fullName }),
        });
        if (!res.ok)
          throw new Error(
            (await res.json()).detail || "Registration failed"
          );
        const data = await res.json();
        set({
          user: data.user,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          isAuthenticated: true,
        });
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return false;
        try {
          const res = await fetch(`${API}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
          if (!res.ok) {
            get().logout();
            return false;
          }
          const data = await res.json();
          set({ accessToken: data.access_token });
          return true;
        } catch {
          get().logout();
          return false;
        }
      },

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    { name: REFRESH_SS_KEY, storage: createJSONStorage(() => sessionStorage), partialize: (s) => ({ refreshToken: s.refreshToken }) }
  )
);
