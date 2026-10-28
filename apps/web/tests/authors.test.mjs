import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadModule, samplePost, webFile } from "./helpers/load-module.mjs";

const anchor = ({ children, href, ...props }) =>
  createElement("a", { href, ...props }, children);
const posts = [
  samplePost,
  {
    ...samplePost,
    id: "money",
    slug: "money-in-uzbekistan",
    title: "Money",
    published_at: "2026-10-28T10:00:00Z",
  },
  {
    ...samplePost,
    id: "ru",
    slug: "dengi",
    language_code: "ru",
    title: "Деньги",
  },
  {
    ...samplePost,
    id: "b",
    slug: "bukhara-by-aziza",
    author_name: "Aziza",
    author_slug: "aziza",
  },
];

test("author profiles are built from published posts, newest first, per language", async () => {
  const { buildAuthorProfiles, findAuthorProfile } =
    await loadModule("lib/authors.ts");
  const profiles = buildAuthorProfiles(posts);
  assert.deepEqual(
    profiles.map((profile) => profile.slug),
    ["aziza", "laziz"],
  );
  const laziz = findAuthorProfile(posts, "laziz");
  assert.equal(laziz.name, "Laziz");
  assert.deepEqual(
    laziz.posts.map((post) => post.slug),
    ["money-in-uzbekistan", "visiting-uzbekistan-first-time", "dengi"],
  );
  assert.equal(laziz.guideCount, 3);
  assert.equal(findAuthorProfile(posts, "nobody"), null);
  assert.equal(findAuthorProfile(posts, "../etc"), null);
});

async function renderAuthor(slug, fetchPosts) {
  const site = await loadModule("lib/site.ts");
  const page = await loadModule("app/authors/[slug]/page.tsx", {
    "next/link": anchor,
    "next/navigation": {
      notFound: () => {
        throw new Error("NEXT_NOT_FOUND");
      },
    },
    "@/lib/site": site,
    "@/lib/authors": await loadModule("lib/authors.ts"),
    "@/lib/editorial-content": {
      listPublishedPosts: fetchPosts,
      SITE_URL: "https://www.uzbekistanos.com",
    },
    "@/components/site/site-header": {
      SiteHeader: () => createElement("header"),
    },
    "@/components/site/site-footer": {
      SiteFooter: () => createElement("footer"),
    },
    "@/components/site/json-ld": await loadModule(
      "components/site/json-ld.tsx",
    ),
    "@/components/site/guide-list": await loadModule(
      "components/site/guide-list.tsx",
      { "next/link": anchor },
    ),
  });
  const params = Promise.resolve({ slug });
  return {
    html: renderToStaticMarkup(await page.default({ params })),
    metadata: await page.generateMetadata({ params }),
  };
}

test("author pages render the profile, Person schema and the author's guides", async () => {
  const { html, metadata } = await renderAuthor("laziz", async () => posts);
  assert.match(metadata.title, /Laziz/);
  assert.equal(
    metadata.alternates.canonical,
    "https://www.uzbekistanos.com/authors/laziz",
  );
  assert.match(html, /<h1[^>]*>Laziz<\/h1>/);
  assert.match(html, /"@type":"Person"/);
  assert.match(html, /Kebab Travel/);
  assert.match(html, /href="\/blog\/money-in-uzbekistan"/);
  assert.match(html, /href="\/blog\/dengi"/);
  assert.doesNotMatch(html, /bukhara-by-aziza/);
});

test("unknown authors return not found", async () => {
  await assert.rejects(
    renderAuthor("nobody", async () => posts),
    /NEXT_NOT_FOUND/,
  );
});

test("articles link their byline and schema to the author page", async () => {
  const article = await webFile("app/blog/[slug]/page.tsx");
  assert.match(article, /authorPageUrl\(post\.author\)/);
  const { authorPageUrl } = await loadModule("lib/authors.ts");
  assert.equal(
    authorPageUrl({ slug: "laziz", profile_url: null }, "https://x.test"),
    "https://x.test/authors/laziz",
  );
  assert.equal(
    authorPageUrl({ slug: "", profile_url: null }, "https://x.test"),
    "https://x.test/about",
  );
  assert.equal(
    authorPageUrl(
      { slug: "laziz", profile_url: "https://laziz.example/me" },
      "https://x.test",
    ),
    "https://laziz.example/me",
  );
  assert.equal(
    authorPageUrl(
      { slug: "laziz", profile_url: "javascript:alert(1)" },
      "https://x.test",
    ),
    "https://x.test/authors/laziz",
  );
});
