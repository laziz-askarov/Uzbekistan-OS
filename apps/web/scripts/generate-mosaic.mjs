// Writes lib/anor-mosaic.svg.ts from public/brand/anor-mosaic.svg so the
// server can lay the mark tile by tile without reading the file at runtime.
import { readFile, writeFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
const svg = await readFile(
  new URL("public/brand/anor-mosaic.svg", root),
  "utf8",
);
if (svg.includes("`") || svg.includes("${")) {
  throw new Error("The mosaic SVG cannot be embedded in a template literal");
}
await writeFile(
  new URL("lib/anor-mosaic.svg.ts", root),
  `// Generated from the brand kit (01-logo/anor-mosaic.svg). Do not edit by hand:\n// run \`pnpm --filter @uzbekistan-os/web brand:mosaic\` after replacing the SVG.\nexport const ANOR_MOSAIC_SVG = \`${svg.trimEnd()}\`;\n`,
);
