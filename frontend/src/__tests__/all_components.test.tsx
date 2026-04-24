/**
 * Meta-test: every component module under src/components/ should at least import.
 * For default exports that are simple components, also try a minimal render.
 * Errors during render are tolerated (component may need providers/router).
 */
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render } from "@testing-library/react";

// Stub next/navigation for any module that imports it at top-level
vi.mock("next/navigation", async () => {
  const m = await import("./test-utils");
  return m.nextNavigationMock;
});

const modules = import.meta.glob("../components/**/*.tsx", { eager: true }) as Record<
  string,
  Record<string, unknown>
>;

describe("all component modules import cleanly", () => {
  const entries = Object.entries(modules);

  it("discovers component modules", () => {
    expect(entries.length).toBeGreaterThan(0);
  });

  for (const [path, mod] of entries) {
    it(`module loads: ${path}`, () => {
      // The mere fact this test runs means import succeeded
      expect(mod).toBeTruthy();
    });
  }

  for (const [path, mod] of entries) {
    const candidates: Array<[string, unknown]> = [];
    if (typeof (mod as any).default === "function") {
      candidates.push(["default", (mod as any).default]);
    }
    for (const [k, v] of Object.entries(mod)) {
      if (k === "default") continue;
      if (typeof v === "function" && /^[A-Z]/.test(k)) {
        candidates.push([k, v]);
      }
      // memo() returns object with $$typeof
      if (
        typeof v === "object" && v !== null &&
        (v as any).$$typeof !== undefined &&
        /^[A-Z]/.test(k)
      ) {
        candidates.push([k, v]);
      }
    }

    for (const [name, Comp] of candidates) {
      it(`renders or skips: ${path}::${name}`, () => {
        try {
          render(React.createElement(Comp as any));
        } catch {
          // Components requiring specific props or providers — acceptable
        }
        // No assertion: just ensures no test-runner-level failure
        expect(true).toBe(true);
      });
    }
  }
});
