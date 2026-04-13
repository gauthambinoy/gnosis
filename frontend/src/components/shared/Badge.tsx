import { clsx } from "clsx";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "primary";
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        {
          "bg-gnosis-border text-gnosis-muted": variant === "default",
          "bg-gnosis-success/10 text-gnosis-success": variant === "success",
          "bg-yellow-500/10 text-yellow-400": variant === "warning",
          "bg-gnosis-error/10 text-gnosis-error": variant === "error",
          "bg-gnosis-primary/10 text-gnosis-primary": variant === "primary",
        },
        className
      )}
    >
      {children}
    </span>
  );
}
