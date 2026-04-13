import { clsx } from "clsx";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={clsx(
        "animate-shimmer rounded-lg bg-gradient-to-r from-gnosis-surface via-gnosis-border/50 to-gnosis-surface bg-[length:200%_100%]",
        className
      )}
    />
  );
}
