import assert from "node:assert/strict";
import test from "node:test";
import { loadModule, webFile } from "./helpers/load-module.mjs";

test("site constants describe Uzbekistan OS by Kebab Travel without account calls to action", async () => {
  const site = await loadModule("lib/site.ts");
  assert.equal(site.SITE_NAME, "Uzbekistan OS");
  assert.equal(site.OPERATOR_NAME, "Kebab Travel");
  assert.match(site.SITE_TAGLINE, /verified guide/i);
  assert.match(site.CONTACT_EMAIL, /@uzbekistanos\.com$/);
  const hrefs = site.PRIMARY_NAVIGATION.map((item) => item.href);
  assert.deepEqual(hrefs, ["/travel", "/living", "/about", "/trips"]);
  assert.ok(!hrefs.includes("/signup"));
  assert.ok(!hrefs.includes("/chat"));
});

test("organization schema names Kebab Travel as publisher of the Uzbekistan OS website", async () => {
  const schema = await loadModule("lib/organization-schema.ts", {
    "@/lib/site": await loadModule("lib/site.ts"),
  });
  const graph = schema.organizationGraph("https://www.uzbekistanos.com");
  assert.equal(graph["@context"], "https://schema.org");
  const organization = graph["@graph"].find(
    (node) => node["@type"] === "Organization",
  );
  const website = graph["@graph"].find((node) => node["@type"] === "WebSite");
  assert.equal(organization.name, "Kebab Travel");
  assert.equal(
    organization["@id"],
    "https://www.uzbekistanos.com/#organization",
  );
  assert.match(organization.email, /@uzbekistanos\.com$/);
  assert.equal(organization.address.addressLocality, "Tashkent");
  assert.equal(organization.address.addressCountry, "UZ");
  assert.equal(website.name, "Uzbekistan OS");
  assert.equal(website.url, "https://www.uzbekistanos.com");
  assert.equal(website.publisher["@id"], organization["@id"]);
  assert.equal(website.inLanguage, "en");
});

test("root layout bundles the brand typefaces and emits organization structured data", async () => {
  const layout = await webFile("app/layout.tsx");
  assert.match(layout, /from "next\/font\/google"/);
  assert.match(layout, /Fraunces/);
  assert.match(layout, /Inter/);
  assert.match(layout, /organizationGraph/);
  assert.match(layout, /<JsonLd/);
  assert.match(layout, /Kebab Travel/);
  assert.match(layout, /title:\s*"Uzbekistan OS by Kebab Travel/);
  assert.doesNotMatch(layout, /visa/i);
});

test("JSON-LD helper escapes closing tags so untrusted strings cannot break out", async () => {
  const { renderToStaticMarkup } = await import("react-dom/server");
  const { createElement } = await import("react");
  const { JsonLd } = await loadModule("components/site/json-ld.tsx");
  const html = renderToStaticMarkup(
    createElement(JsonLd, { data: { name: "</script><b>x" } }),
  );
  assert.match(html, /type="application\/ld\+json"/);
  assert.doesNotMatch(html, /<\/script><b>/);
  assert.match(html, /\\u003c\/script>/);
});

test("robots explicitly welcomes search and AI answer crawlers on public pages only", async () => {
  const robots = await webFile("app/robots.ts");
  for (const bot of [
    "Googlebot",
    "Bingbot",
    "GPTBot",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-SearchBot",
    "PerplexityBot",
    "Google-Extended",
    "Applebot",
    "CCBot",
  ]) {
    assert.match(robots, new RegExp(`"${bot}"`), bot);
  }
  assert.match(robots, /\/admin\//);
  assert.match(robots, /\/chat/);
  assert.match(robots, /sitemap\.xml/);
});

test("LLM index and sitemap describe the travel reference, hubs, trips and about pages", async () => {
  const [llms, sitemap, og] = await Promise.all([
    webFile("app/llms.txt/route.ts"),
    webFile("app/sitemap.ts"),
    webFile("app/opengraph-image.tsx"),
  ]);
  assert.match(llms, /by Kebab Travel/);
  assert.match(llms, /verified/i);
  for (const path of ["/travel", "/living", "/trips", "/about"]) {
    assert.match(llms, new RegExp(`\\$\\{SITE_URL\\}${path}`), path);
    assert.match(sitemap, new RegExp(`\\$\\{SITE_URL\\}${path}`), path);
  }
  assert.doesNotMatch(llms, /Product overview and visa guidance/);
  assert.match(og, /Kebab Travel/);
  assert.match(og, /verified guide/i);
});
