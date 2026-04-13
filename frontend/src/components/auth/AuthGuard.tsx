"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, setLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    setLoading(false);
  }, [setLoading]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-[#C8FF00] border-t-transparent rounded-full animate-spin" />
          <span className="text-[#707070] text-sm">Loading Gnosis...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return <>{children}</>;
}
