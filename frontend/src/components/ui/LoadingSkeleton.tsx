"use client";

import { motion } from "framer-motion";

function Pulse({ className = "" }: { className?: string }) {
  return (
    <motion.div
      className={`bg-white/[0.06] rounded-lg ${className}`}
      animate={{ opacity: [0.3, 0.6, 0.3] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5 space-y-4">
      <Pulse className="h-4 w-1/3" />
      <Pulse className="h-3 w-2/3" />
      <Pulse className="h-3 w-1/2" />
      <div className="flex gap-2 pt-2">
        <Pulse className="h-8 w-20 rounded-full" />
        <Pulse className="h-8 w-20 rounded-full" />
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      <div className="flex gap-4 pb-2 border-b border-white/[0.06]">
        <Pulse className="h-3 w-24" />
        <Pulse className="h-3 w-32" />
        <Pulse className="h-3 w-20" />
        <Pulse className="h-3 w-16" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 py-2">
          <Pulse className="h-3 w-24" />
          <Pulse className="h-3 w-32" />
          <Pulse className="h-3 w-20" />
          <Pulse className="h-3 w-16" />
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex gap-2 items-center">
        <Pulse className="h-8 w-48" />
        <Pulse className="h-8 w-8 rounded-full ml-auto" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
          <Pulse className="h-4 w-32 mb-4" />
          <Pulse className="h-48 w-full" />
        </div>
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
          <Pulse className="h-4 w-32 mb-4" />
          <TableSkeleton rows={4} />
        </div>
      </div>
    </div>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5 space-y-3">
      <div className="flex items-center gap-3">
        <Pulse className="h-10 w-10 rounded-full" />
        <div className="space-y-2 flex-1">
          <Pulse className="h-4 w-32" />
          <Pulse className="h-3 w-48" />
        </div>
      </div>
      <Pulse className="h-2 w-full rounded-full" />
      <div className="flex justify-between pt-1">
        <Pulse className="h-3 w-16" />
        <Pulse className="h-3 w-20" />
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6 p-6 animate-in fade-in duration-300">
      <Pulse className="h-8 w-56" />
      <Pulse className="h-4 w-96" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <AgentCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
