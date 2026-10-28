import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadModule, samplePost } from "./helpers/load-module.mjs";

const anchor = ({ children, href, ...props }) =>
  createElement("a", { href, ...props }, children);

const posts = [
  samplePost,
  {
    ...samplePost,
    id: "visa",
    slug: "uzbekistan-visa-requirements",
    title: "Visa requirements",
  },
  {
    ...samplePost,
    id: "money",
    slug: "money-in-uzbekistan",
    title: "Money in Uzbekistan",
  },
  {
    ...samplePost,
    id: "trains",
    slug: "getting-around-uzbekistan",
    title: "Getting around",
  },
  {
    ...samplePost,
    id: "food",
    slug: "what-to-eat-in-uzbekistan",
    title: "What to eat",
  },
  { ...samplePost, id: "novel", slug: "brand-new-topic", title: "A new guide" },
  {
    ...samplePost,
    id: "ru",
    slug: "pervaya-poezdka",
    language_code: "ru",
    title: "Первая поездка",
  },
  {
    ...samplePost,
    id: "llc",
    slug: "start-an-llc",
    domain_slug: "business-registration",
    title: "Start an LLC",
  },
];

test("travel guides are grouped into fixed planning clusters with unknown guides kept visible", async () => {
  const { groupTravelGuides, TRAVEL_CLUSTERS } = await loadModule(
    "lib/guide-clusters.ts",
  );
  assert.deepEqual(
    TRAVEL_CLUSTERS.map((cluster) => cluster.id),
    ["before-you-go", "getting-around", "where-to-go", "culture-and-food"],
  );
  const grouped = groupTravelGuides(posts);
  const bySlug = (id) =>
    grouped.find((group) => group.id === id).posts.map((post) => post.slug);
  assert.deepEqual(bySlug("before-you-go"), [
    "uzbekistan-visa-requirements",
    "money-in-uzbekistan",
  ]);
  assert.deepEqual(bySlug("getting-around"), ["getting-around-uzbekistan"]);
  assert.deepEqual(bySlug("where-to-go"), ["visiting-uzbekistan-first-time"]);
  assert.deepEqual(bySlug("culture-and-food"), ["what-to-eat-in-uzbekistan"]);
  const more = grouped.find((group) => group.id === "more-guides");
  assert.deepEqual(
    more.posts.map((post) => post.slug),
    ["brand-new-topic"],
  );
  assert.ok(
    !grouped
      .flatMap((group) => group.posts)
      .some((post) => post.domain_slug !== "tourism"),
  );
});

test("living guides are grouped by civic domain in a fixed order", async () => {
  const { groupLivingGuides, LIVING_DOMAINS } = await loadModule(
    "lib/guide-clusters.ts",
  );
  assert.deepEqual(
    LIVING_DOMAINS.map((domain) => domain.slug),
    ["immigration", "everyday-living", "business-registration", "healthcare"],
  );
  const grouped = groupLivingGuides(posts);
  assert.deepEqual(
    grouped.map((group) => [group.slug, group.posts.length]),
    [["business-registration", 1]],
  );
});

async function renderHub(path, fetchPosts) {
  const site = await loadModule("lib/site.ts");
  const clusters = await loadModule("lib/guide-clusters.ts");
  const page = await loadModule(path, {
    "next/link": anchor,
    "@/lib/site": site,
    "@/lib/guide-clusters": clusters,
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
    "@/components/site/guide-list": await loadModule(
      "components/site/guide-list.tsx",
      {
        "next/link": anchor,
      },
    ),
  });
  return {
    html: renderToStaticMarkup(await page.default()),
    metadata: page.metadata,
  };
}

test("the travel hub renders every cluster with guide links and verification dates", async () => {
  const { html, metadata } = await renderHub(
    "app/travel/page.tsx",
    async (options) => {
      assert.equal(options.language, "en");
      return posts;
    },
  );
  assert.match(metadata.title, /travel guides/i);
  assert.equal(
    metadata.alternates.canonical,
    "https://www.uzbekistanos.com/travel",
  );
  assert.match(html, /<h1[^>]*>[^<]*Uzbekistan travel guides/);
  assert.match(html, /id="before-you-go"/);
  assert.match(html, /href="\/blog\/money-in-uzbekistan"/);
  assert.match(html, /href="\/blog\/brand-new-topic"/);
  assert.match(html, /dateTime="2026-10-28T09:00:00Z"/);
  assert.doesNotMatch(html, /pervaya-poezdka|start-an-llc/);
  assert.match(html, /href="\/trips"/);
});

test("the living hub lists civic guides by domain and invites readers when a domain is empty", async () => {
  const { html, metadata } = await renderHub(
    "app/living/page.tsx",
    async () => posts,
  );
  assert.match(metadata.title, /living in Uzbekistan/i);
  assert.match(html, /<h1[^>]*>[^<]*Living in Uzbekistan/);
  assert.match(html, /href="\/blog\/start-an-llc"/);
  assert.doesNotMatch(html, /visiting-uzbekistan-first-time/);
  const empty = await renderHub("app/living/page.tsx", async () => {
    throw new Error("API unavailable");
  });
  assert.match(empty.html, /href="\/blog"/);
  assert.doesNotMatch(empty.html, /undefined|API unavailable/);
});
