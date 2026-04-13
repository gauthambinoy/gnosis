import { useAuth } from "./auth";

const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private getHeaders(): HeadersInit {
    const token = useAuth.getState().accessToken;
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async fetch(path: string, options: RequestInit = {}): Promise<Response> {
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...this.getHeaders(), ...options.headers },
    });

    // Auto-refresh on 401
    if (res.status === 401) {
      const refreshed = await useAuth.getState().refreshAccessToken();
      if (refreshed) {
        return fetch(`${API}${path}`, {
          ...options,
          headers: { ...this.getHeaders(), ...options.headers },
        });
      }
      useAuth.getState().logout();
      if (typeof window !== "undefined") window.location.href = "/login";
    }

    return res;
  }

  async get(path: string) {
    return this.fetch(path);
  }

  async post(path: string, body?: unknown) {
    return this.fetch(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put(path: string, body: unknown) {
    return this.fetch(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  async delete(path: string) {
    return this.fetch(path, { method: "DELETE" });
  }
}

export const api = new ApiClient();
