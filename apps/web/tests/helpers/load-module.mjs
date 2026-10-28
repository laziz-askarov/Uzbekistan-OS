import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import ts from "typescript";

const require = createRequire(import.meta.url);
const webRoot = new URL("../../", import.meta.url);

/**
 * Transpile a TypeScript/TSX source file from apps/web and evaluate it with
 * mocked module specifiers. Unmocked specifiers resolve through Node.
 */
export async function loadModule(path, mocks = {}) {
  const source = await readFile(new URL(path, webRoot), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const loaded = { exports: {} };
  new Function("require", "module", "exports", output)(
    (name) => {
      if (name in mocks) return mocks[name];
      if (name.endsWith(".css")) return new Proxy({}, { get: (_, key) => String(key) });
      return require(name);
    },
    loaded,
    loaded.exports,
  );
  return loaded.exports;
}

export async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

export const samplePost = {
  id: "post-first-trip",
  slug: "visiting-uzbekistan-first-time",
  translation_group_id: "group-first-trip",
  content_type: "guide",
  domain_slug: "tourism",
  language_code: "en",
  title: "Visiting Uzbekistan for the First Time",
  summary: "A seven-day journey through Tashkent, Samarkand, and Bukhara.",
  hero_image_url: "https://images.example/registan.webp",
  hero_image_alt: "Registan Square in Samarkand",
  author_name: "Laziz",
  author_slug: "laziz",
  published_at: "2026-10-27T21:41:30Z",
  updated_at: "2026-10-28T09:00:00Z",
};
