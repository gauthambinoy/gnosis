import { clsx } from "clsx";
import { ReactNode } from "react";

interface GlowEffectProps {
  children: ReactNode;
  color?: string;
  className?: string;
}

export function GlowEffect({ children, color = "rgba(200,255,0,0.15)", className }: GlowEffectProps) {
  return (
    <div className={clsx("relative group", className)}>
      <div
        className="absolute -inset-0.5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl"
        style={{ background: color }}
      />
      <div className="relative">{children}</div>
    </div>
  );
}
