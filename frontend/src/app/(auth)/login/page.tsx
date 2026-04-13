"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/shared/Button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(API_URL + "/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Login failed");
      }
      const data = await res.json();
      localStorage.setItem("gnosis_token", data.access_token);
      localStorage.setItem("gnosis_refresh", data.refresh_token);
      window.location.href = "/nerve-center";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-4xl font-bold text-gnosis-primary">◎ GNOSIS</h1>
          <p className="text-gnosis-muted mt-2">The Knowledge That Works</p>
        </div>
        <form onSubmit={handleLogin} className="space-y-4 bg-gnosis-surface border border-gnosis-border rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-gnosis-text text-center mb-4">Sign In</h2>
          {error && <p className="text-red-400 text-sm text-center">{error}</p>}
          <div>
            <label className="text-sm text-gnosis-muted mb-1 block">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50" />
          </div>
          <div>
            <label className="text-sm text-gnosis-muted mb-1 block">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50" />
          </div>
          <Button type="submit" disabled={loading} className="w-full">{loading ? "Signing in..." : "Sign In"}</Button>
          <p className="text-center text-sm text-gnosis-muted">
            No account? <Link href="/signup" className="text-gnosis-primary hover:underline">Create one</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
