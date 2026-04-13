import { clsx } from "clsx";
import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
}

export function Card({ children, className, glow = false }: CardProps) {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-gnosis-border bg-gnosis-surface p-6 transition-all duration-300",
        glow && "hover:shadow-[0_0_40px_rgba(200,255,0,0.08)] hover:border-gnosis-primary/30",
        className
      )}
    >
      {children}
    </div>
  );
}
