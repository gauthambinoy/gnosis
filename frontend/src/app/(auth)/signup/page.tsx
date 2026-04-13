"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/shared/Button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SignupPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(API_URL + "/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Registration failed");
      }
      const data = await res.json();
      localStorage.setItem("gnosis_token", data.access_token);
      localStorage.setItem("gnosis_refresh", data.refresh_token);
      window.location.href = "/nerve-center";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-4xl font-bold text-gnosis-primary">◎ GNOSIS</h1>
          <p className="text-gnosis-muted mt-2">Begin Your Journey</p>
        </div>
        <form onSubmit={handleSignup} className="space-y-4 bg-gnosis-surface border border-gnosis-border rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-gnosis-text text-center mb-4">Create Account</h2>
          {error && <p className="text-red-400 text-sm text-center">{error}</p>}
          <div>
            <label className="text-sm text-gnosis-muted mb-1 block">Full Name</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} required className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50" />
          </div>
          <div>
            <label className="text-sm text-gnosis-muted mb-1 block">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50" />
          </div>
          <div>
            <label className="text-sm text-gnosis-muted mb-1 block">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} className="w-full bg-gnosis-bg border border-gnosis-border rounded-xl px-4 py-2.5 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50" />
          </div>
          <Button type="submit" disabled={loading} className="w-full">{loading ? "Creating..." : "Create Account"}</Button>
          <p className="text-center text-sm text-gnosis-muted">
            Already have an account? <Link href="/login" className="text-gnosis-primary hover:underline">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
