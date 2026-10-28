import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const post = {
  id: "first-trip",
  slug: "visiting-uzbekistan-first-time",
  language_code: "en",
  domain_slug: "tourism",
  title: "Visiting Uzbekistan",
  summary: "Plan your first trip.",
  hero_image_url: "https://images.example/registan.webp",
  hero_image_alt: "Registan Square in Samarkand",
  published_at: "2026-10-28T01:00:00Z",
};
async function renderIndex(parameters = {}, posts = [post]) {
  const calls = [];
  const source = await readFile(
    new URL("../app/blog/page.tsx", import.meta.url),
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
    "@/lib/editorial-content": {
      SITE_URL: "https://www.uzbekistanos.com",
      listPublishedPosts: async (options) => {
        calls.push(options);
        return posts;
      },
    },
    "./blog.module.css": {},
  };
  const loaded = { exports: {} };
  new Function("require", "module", "exports", output)(
    (name) => mocks[name] ?? require(name),
    loaded,
    loaded.exports,
  );
  const element = await loaded.exports.default({
    searchParams: Promise.resolve(parameters),
  });
  return { html: renderToStaticMarkup(element), calls };
}

test("blog listing defaults to English and omits the language filter", async () => {
  for (const parameters of [{}, { language: "" }, { language: "invalid" }]) {
    const { html, calls } = await renderIndex(parameters);
    assert.deepEqual(calls, [
      { domain: undefined, language: "en", limit: 100 },
    ]);
    assert.doesNotMatch(
      html,
      /All languages|Filter guides by language|all-languages/,
    );
    assert.match(html, /Filter guides by topic/);
    assert.match(html, /href="\/blog\?domain=tourism"/);
    assert.doesNotMatch(html, /language=en/);
  }
});

test("topic filters preserve explicit localized article navigation", async () => {
  for (const language of ["uz", "ru"]) {
    const { html, calls } = await renderIndex({
      domain: "immigration",
      language,
    });
    assert.deepEqual(calls, [{ domain: "immigration", language, limit: 100 }]);
    assert.match(
      html,
      new RegExp(`href="/blog\\?domain=tourism&amp;language=${language}"`),
    );
    assert.doesNotMatch(html, /Filter guides by language/);
  }
  const { calls } = await renderIndex({ domain: "unknown" });
  assert.equal(calls[0].domain, undefined);
});

test("each blog card renders its featured image with alt text and reserved dimensions", async () => {
  const { html } = await renderIndex({}, [
    post,
    {
      ...post,
      id: "visa",
      slug: "visa",
      hero_image_url: "https://images.example/airport.webp",
      hero_image_alt: "Tashkent airport",
    },
    {
      ...post,
      id: "season",
      slug: "season",
      hero_image_url: "https://images.example/chimgan.webp",
      hero_image_alt: "Chimgan hills",
    },
  ]);
  assert.equal((html.match(/<img /g) ?? []).length, 3);
  for (const alt of [post.hero_image_alt, "Tashkent airport", "Chimgan hills"])
    assert.ok(html.includes(`alt="${alt}"`));
  assert.equal(
    (
      html.match(
        /width="1600" height="1000" loading="lazy" decoding="async"/g,
      ) ?? []
    ).length,
    3,
  );
  assert.match(html, /aria-labelledby="blog-title-first-trip"/);
  assert.match(
    html,
    /<h2 id="blog-title-first-trip">Visiting Uzbekistan<\/h2>/,
  );
  assert.match(html, /href="\/blog\/visiting-uzbekistan-first-time"/);
});

test("cards remain readable when imagery is missing or unsafe", async () => {
  for (const url of [
    null,
    "invalid",
    "javascript:alert(1)",
    "data:image/svg+xml,bad",
  ]) {
    const { html } = await renderIndex({}, [{ ...post, hero_image_url: url }]);
    assert.doesNotMatch(html, /<img/);
    assert.match(html, /Visiting Uzbekistan/);
    assert.match(html, /Read guide/);
  }
  const { html } = await renderIndex({}, [{ ...post, hero_image_alt: null }]);
  assert.match(html, /alt="Visiting Uzbekistan"/);
});

test("empty English topics retain navigation and a useful empty state", async () => {
  const { html } = await renderIndex({ domain: "healthcare" }, []);
  assert.match(html, /No published guides in this topic yet/);
  assert.match(html, /Filter guides by topic/);
  assert.doesNotMatch(html, /<img/);
});
