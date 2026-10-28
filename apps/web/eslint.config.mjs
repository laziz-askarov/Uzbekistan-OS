import { defineConfig, globalIgnores } from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextCoreWebVitals,
  ...nextTypeScript,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  {
    rules: {
      // Authentication and account flows navigate with a full page load on
      // purpose so the server picks up the refreshed Supabase session cookies.
      "@next/next/no-location-assign-relative-destination": "off",
    },
  },
]);
