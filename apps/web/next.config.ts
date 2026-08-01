import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  transpilePackages: ["@uzbekistan-os/design-system"],
  turbopack: {
    root: repositoryRoot,
  },
};

export default nextConfig;
