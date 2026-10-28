import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadModule, samplePost } from "./helpers/load-module.mjs";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const pageSource = readFileSync(`${webRoot}/app/page.tsx`, "utf8");
const signupSource = readFileSync(`${webRoot}/app/signup/page.tsx`, "utf8");

const anchor = ({ children, href, ...props }) =>
  createElement("a", { href, ...props }, children);

async function renderHome(fetchPosts) {
  const site = await loadModule("lib/site.ts");
  const clusters = await loadModule("lib/guide-clusters.ts");
  const header = await loadModule("components/site/site-header.tsx", {
    "next/link": anchor,
    "@/lib/site": site,
  });
  const footer = await loadModule("components/site/site-footer.tsx", {
    "next/link": anchor,
    "@/lib/site": site,
  });
  const page = await loadModule("app/page.tsx", {
    "next/link": anchor,
    "next/image": ({ alt, src }) => createElement("img", { alt, src }),
    "@/lib/site": site,
    "@/lib/guide-clusters": clusters,
    "@/lib/editorial-content": { listPublishedPosts: fetchPosts },
    "@/components/site/site-header": header,
    "@/components/site/site-footer": footer,
    "@/components/site/guide-list": await loadModule(
      "components/site/guide-list.tsx",
      { "next/link": anchor },
    ),
    "@/components/editorial/latest-blogs": {
      __esModule: true,
      default: () => createElement("section", { id: "latest-blogs" }),
    },
  });
  return renderToStaticMarkup(await page.default());
}

test("landing page leads with the verified travel guide, not visa assistance", async () => {
  const html = await renderHome(async () => [samplePost]);
  assert.match(html, /The verified guide to travelling in Uzbekistan/);
  assert.match(html, /<h1[^>]*>[^<]*checked, dated and sourced/);
  assert.match(html, /href="\/blog\/visiting-uzbekistan-first-time"/);
  assert.match(html, /href="\/trips"/);
  assert.match(html, /Kebab Travel/);
  assert.match(html, /Last verified/);
  assert.doesNotMatch(
    html,
    /Create free account|Find the right visa|visa workspace/i,
  );
  assert.doesNotMatch(html, /href="\/signup"/);
});

test("landing page guides travellers through planning, destinations, living and the trip service in order", async () => {
  const html = await renderHome(async () => [samplePost]);
  const order = [
    'id="hero"',
    'id="before-you-go"',
    'id="where-to-go"',
    'id="latest-blogs"',
    'id="living"',
    'id="plan-a-trip"',
    'id="how-we-verify"',
  ].map((marker) => html.indexOf(marker));
  assert.ok(
    order.every((index) => index >= 0),
    String(order),
  );
  assert.deepEqual(
    order,
    [...order].sort((a, b) => a - b),
  );
  assert.match(html, /href="\/travel"/);
  assert.match(html, /href="\/living"/);
  assert.match(html, /href="\/about#methodology"/);
  for (const city of ["Tashkent", "Samarkand", "Bukhara", "Khiva"]) {
    assert.match(html, new RegExp(city));
  }
});

test("landing page stays useful when the editorial API is unavailable", async () => {
  const html = await renderHome(async () => {
    throw new Error("API unavailable");
  });
  assert.match(html, /href="\/trips"/);
  assert.match(html, /href="\/blog"/);
  assert.doesNotMatch(html, /undefined|API unavailable/);
});

test("landing page source keeps the visa catalogue out and links only to official or internal destinations", () => {
  assert.doesNotMatch(pageSource, /"D-1"|"PV-1"|visa-catalogue|common-visas/);
  assert.doesNotMatch(pageSource, /visarun|advantour|wikipedia|facebook/);
  assert.match(pageSource, /<SiteHeader/);
  assert.match(pageSource, /<SiteFooter/);
  assert.match(pageSource, /<Suspense fallback=\{null\}>\s*<LatestBlogs \/>/);
});

test("signup screen requires an account and offers email with phone fallback", () => {
  assert.match(signupSource, /Create your free account/);
  assert.match(signupSource, /Register with email and a password/);
  assert.match(signupSource, /verify your number by SMS/);
  assert.match(signupSource, /<AuthForm \/>/);
  assert.doesNotMatch(signupSource, /Continue as guest/);
});

test("landing page keeps the hero photograph local", () => {
  assert.match(pageSource, /\/landing\/hero-background\.avif/);
  assert.equal(
    existsSync(`${webRoot}/public/landing/hero-background.avif`),
    true,
  );
});
