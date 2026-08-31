import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("the blog is server rendered from published-only API endpoints", async () => {
  const [data, index, article] = await Promise.all([
    webFile("lib/editorial-content.ts"),
    webFile("app/blog/page.tsx"),
    webFile("app/blog/[slug]/page.tsx"),
  ]);

  assert.match(data, /GROUNDED_API_BASE_URL/);
  assert.match(data, /\/content\/posts\?/);
  assert.match(data, /\/content\/posts\/\$\{encodeURIComponent\(slug\)\}/);
  assert.match(
    data,
    /next: \{ revalidate: 300, tags: \["editorial-content"\] \}/,
  );
  assert.doesNotMatch(index, /"use client"/);
  assert.doesNotMatch(article, /"use client"/);
  assert.match(article, /if \(!post\) notFound\(\)/);
});

test("articles expose canonical, language, social, author, and source metadata", async () => {
  const article = await webFile("app/blog/[slug]/page.tsx");

  assert.match(article, /generateMetadata/);
  assert.match(article, /languages: languageAlternates/);
  assert.match(article, /"text\/markdown"/);
  assert.match(article, /type: "article"/);
  assert.match(article, /"@type": "BlogPosting"/);
  assert.match(article, /"@type": "BreadcrumbList"/);
  assert.match(article, /"@type": "FAQPage"/);
  assert.match(article, /citation: post\.sources\.map/);
  assert.match(article, /Sources and review trail/);
  assert.match(article, /About the author/);
  assert.match(article, /replace\(\s*\/</);
});

test("crawler and LLM discovery surfaces include only published article links", async () => {
  const [sitemap, robots, llms, full, markdown, rss] = await Promise.all([
    webFile("app/sitemap.ts"),
    webFile("app/robots.ts"),
    webFile("app/llms.txt/route.ts"),
    webFile("app/llms-full.txt/route.ts"),
    webFile("app/blog/[slug]/markdown/route.ts"),
    webFile("app/blog/rss.xml/route.ts"),
  ]);

  assert.match(sitemap, /listPublishedPosts/);
  assert.match(sitemap, /publicPostUrl/);
  assert.match(robots, /\/admin\//);
  assert.match(robots, /sitemap\.xml/);
  assert.match(llms, /Full guide corpus/);
  assert.match(llms, /Published guides/);
  assert.match(full, /complete published guide corpus/);
  assert.match(markdown, /text\/markdown; charset=utf-8/);
  assert.match(markdown, /Reviewed sources/);
  assert.match(rss, /listPublishedPosts/);
  assert.match(rss, /dynamic = "force-dynamic"/);
  assert.match(rss, /application\/rss\+xml; charset=utf-8/);
  assert.match(rss, /<rss version="2\.0"/);
  assert.match(rss, /escapeXml/);
});

test("the site and every article have generated social images", async () => {
  const [rootImage, blogImage, articleImage, article] = await Promise.all([
    webFile("app/opengraph-image.tsx"),
    webFile("app/blog/opengraph-image.tsx"),
    webFile("app/blog/[slug]/opengraph-image.tsx"),
    webFile("app/blog/[slug]/page.tsx"),
  ]);

  for (const image of [rootImage, blogImage, articleImage]) {
    assert.match(image, /ImageResponse/);
    assert.match(image, /width: 1200/);
    assert.match(image, /height: 630/);
    assert.match(image, /contentType = "image\/png"/);
  }
  assert.match(articleImage, /getPublishedPost/);
  assert.match(article, /generatedImage/);
  assert.match(article, /card: "summary_large_image"/);
});

test("Markdown is rendered without accepting raw HTML", async () => {
  const renderer = await webFile("components/editorial/markdown-content.tsx");

  assert.doesNotMatch(renderer, /dangerouslySetInnerHTML/);
  assert.match(renderer, /safeHref/);
  assert.match(renderer, /url\.protocol === "https:"/);
  assert.match(renderer, /<h2 id=\{id\}/);
  assert.match(renderer, /<blockquote/);
});
