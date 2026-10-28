import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";

const require = createRequire(import.meta.url);
async function load(path, mocks = {}) {
  const source = await readFile(new URL(`../${path}`, import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText;
  const loaded = { exports: {} };
  new Function("require", "module", "exports", output)(
    (name) => mocks[name] ?? require(name),
    loaded,
    loaded.exports,
  );
  return loaded.exports;
}
const origin = "https://www.uzbekistanos.com";
const translations = ["en", "uz", "ru"].map((language_code) => ({
  language_code,
  slug: `article-${language_code}`,
  title: language_code,
}));

for (const [language, expected, locale] of [
  ["en", "Key takeaways", "en_US"],
  ["uz", "Asosiy xulosalar", "uz_UZ"],
  ["ru", "Главное", "ru_RU"],
]) {
  test(`${language} articles render localized chrome and reciprocal language metadata`, async () => {
    const labels = await load("lib/editorial-locale.ts");
    const post = {
      slug: `article-${language}`,
      language_code: language,
      canonical_url: `${origin}/blog/article-${language}`,
      title: "Test title",
      summary: "Test summary",
      seo_title: "Local SEO",
      seo_description: "Local description",
      content_type: "article",
      domain_slug: "tourism",
      version_number: 1,
      published_at: "2026-10-28T01:00:00Z",
      updated_at: "2026-10-28T02:00:00Z",
      author: { name: "Laziz", profile_url: null, bio: null },
      hero_image_url: "https://media.example/hero.webp",
      hero_image_alt: "Local image description",
      body_markdown: "Local body",
      sources: [],
      translations,
      structured_content: {
        key_takeaways: ["Local takeaway"],
        faq: [{ question: "Local question?", answer: "Local answer" }],
      },
    };
    const page = await load("app/blog/[slug]/page.tsx", {
      "@/lib/authors": await load("lib/authors.ts"),
      "@/lib/editorial-content": {
        SITE_URL: origin,
        publicPostUrl: (slug) => `${origin}/blog/${slug}`,
        getPublishedPost: async () => post,
      },
      "@/lib/editorial-locale": labels,
      "@/components/editorial/markdown-content": {
        MarkdownContent: ({ markdown }) => createElement("p", null, markdown),
      },
      "next/link": {
        __esModule: true,
        default: ({ children, ...props }) =>
          createElement("a", props, children),
      },
      "next/navigation": {
        notFound: () => {
          throw new Error("not found");
        },
      },
      "../blog.module.css": {},
    });
    const props = { params: Promise.resolve({ slug: post.slug }) };
    const html = renderToStaticMarkup(await page.default(props));
    const text = labels.editorialLabels(language);
    assert.match(html, new RegExp(`lang="${language}"`));
    assert.ok(html.includes(expected));
    assert.ok(html.includes(text.faq));
    assert.ok(html.includes(text.author));
    assert.ok(html.includes(text.published));
    assert.ok(
      html.includes(
        new Intl.DateTimeFormat(language, {
          dateStyle: "long",
          timeZone: "UTC",
        }).format(new Date(post.published_at)),
      ),
    );
    assert.match(
      html,
      new RegExp(
        `href="/blog/article-${language}" hrefLang="${language}" aria-current="page"`,
      ),
    );
    for (const item of translations)
      assert.ok(html.includes(`href="/blog/${item.slug}"`));
    const graph = JSON.parse(html.match(/<script[^>]*>(.*?)<\/script>/s)[1])[
      "@graph"
    ];
    assert.equal(graph[0].inLanguage, language);
    assert.equal(
      graph.find((item) => item["@type"] === "FAQPage").mainEntity[0]
        .acceptedAnswer.text,
      "Local answer",
    );
    const metadata = await page.generateMetadata(props);
    assert.equal(metadata.alternates.canonical, post.canonical_url);
    assert.deepEqual(metadata.alternates.languages, {
      en: `${origin}/blog/article-en`,
      uz: `${origin}/blog/article-uz`,
      ru: `${origin}/blog/article-ru`,
      "x-default": `${origin}/blog/article-en`,
    });
    assert.equal(metadata.openGraph.locale, locale);
    assert.equal(metadata.openGraph.alternateLocale.length, 2);
    assert.equal(metadata.description, post.seo_description);
    assert.equal(metadata.openGraph.images[0].alt, post.hero_image_alt);
  });
}

test("editorial labels support language subtags and an English fallback", async () => {
  const { editorialLabels } = await load("lib/editorial-locale.ts");
  assert.equal(editorialLabels("uz-Latn").faq, "Ko‘p beriladigan savollar");
  assert.equal(editorialLabels("ru-RU").author, "Об авторе");
  assert.equal(editorialLabels("fr").home, "Home");
});
