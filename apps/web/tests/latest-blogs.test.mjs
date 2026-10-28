import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const post = {
  id: "published-first-trip",
  slug: "visiting-uzbekistan-first-time",
  language_code: "en",
  domain_slug: "tourism",
  title: "Visiting Uzbekistan for the First Time",
  summary: "A seven-day journey through Tashkent, Samarkand, and Bukhara.",
  hero_image_url: "https://images.example/registan.webp",
  hero_image_alt: "Registan Square in Samarkand",
  published_at: "2026-10-27T21:41:30Z",
};
async function renderSection(fetchPosts) {
  const source = await readFile(
    new URL("../components/editorial/latest-blogs.tsx", import.meta.url),
    "utf8",
  );
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText;
  const mocks = {
    "next/link": ({ children, ...props }) =>
      createElement("a", props, children),
    "@/lib/editorial-content": { listPublishedPosts: fetchPosts },
    "./latest-blogs.module.css": {},
  };
  const loaded = { exports: {} };
  new Function("require", "module", "exports", output)(
    (name) => mocks[name] ?? require(name),
    loaded,
    loaded.exports,
  );
  return renderToStaticMarkup(await loaded.exports.default());
}

test("homepage blogs render published article links, imagery and dates on the server", async () => {
  const html = await renderSection(async (options) => {
    assert.deepEqual(options, { language: "en", limit: 3 });
    return [post];
  });
  assert.match(html, /aria-labelledby="latest-blogs-title"/);
  assert.match(html, /<h2 id="latest-blogs-title">Latest guides<\/h2>/);
  assert.match(html, /href="\/blog\/visiting-uzbekistan-first-time"/);
  assert.match(
    html,
    /<h3 id="latest-blog-published-first-trip">Visiting Uzbekistan for the First Time<\/h3>/,
  );
  assert.match(html, /alt="Registan Square in Samarkand"/);
  assert.match(html, /loading="lazy"/);
  assert.match(html, /dateTime="2026-10-27T21:41:30Z"/);
  assert.match(html, /A seven-day journey/);
  assert.match(html, /href="\/blog">All guides/);
});

test("latest blogs supports several publications without duplicating cards", async () => {
  const html = await renderSection(async () => [
    post,
    { ...post, id: "second", slug: "bukhara", title: "Explore Bukhara" },
    { ...post, id: "third", slug: "khiva", title: "Explore Khiva" },
  ]);
  assert.equal((html.match(/<article /g) ?? []).length, 3);
  assert.match(html, /href="\/blog\/bukhara"/);
  assert.match(html, /href="\/blog\/khiva"/);
});

test("an unavailable or empty editorial library leaves a usable blog link", async () => {
  for (const fetcher of [
    async () => [],
    async () => {
      throw new Error("API unavailable");
    },
  ]) {
    const html = await renderSection(fetcher);
    assert.match(html, /href="\/blog"/);
    assert.doesNotMatch(html, /<article/);
    assert.doesNotMatch(html, /undefined|API unavailable/);
  }
});

test("cards remain usable without cover imagery and do not render unsafe image URLs", async () => {
  for (const url of [null, "javascript:alert(1)", "data:image/svg+xml,bad"]) {
    const html = await renderSection(async () => [
      { ...post, hero_image_url: url },
    ]);
    assert.match(html, /href="\/blog\/visiting-uzbekistan-first-time"/);
    assert.doesNotMatch(html, /<img/);
  }
});

test("homepage places the blog section after the planning guides and before the living pillar", async () => {
  const source = await readFile(
    new URL("../app/page.tsx", import.meta.url),
    "utf8",
  );
  assert.ok(
    source.indexOf("<LatestBlogs />") > source.indexOf('id="where-to-go"'),
  );
  assert.ok(source.indexOf("<LatestBlogs />") < source.indexOf('id="living"'));
  assert.match(source, /<Suspense fallback=\{null\}>\s*<LatestBlogs \/>/);
});
