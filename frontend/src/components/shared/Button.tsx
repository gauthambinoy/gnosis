"use client";

import { forwardRef, ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          "inline-flex items-center justify-center rounded-xl font-medium transition-all duration-200",
          {
            "bg-gnosis-primary text-gnosis-bg hover:shadow-[0_0_30px_rgba(200,255,0,0.3)] active:scale-[0.98]":
              variant === "primary",
            "border border-gnosis-border text-gnosis-text hover:border-gnosis-primary hover:text-gnosis-primary":
              variant === "secondary",
            "text-gnosis-muted hover:text-gnosis-text":
              variant === "ghost",
          },
          {
            "px-3 py-1.5 text-sm": size === "sm",
            "px-4 py-2 text-sm": size === "md",
            "px-6 py-3 text-base": size === "lg",
          },
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export { Button };
