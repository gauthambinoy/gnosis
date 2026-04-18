import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // React 19 / React-Compiler advisory rule. It flags legitimate patterns
      // (loading initial state from localStorage on mount, syncing state to
      // a changed prop/route, standard data-fetching effects). We keep it on
      // as a warning so it still surfaces in editor + CI logs but does not
      // block builds. Re-evaluate once we adopt useSyncExternalStore /
      // React Compiler everywhere.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
