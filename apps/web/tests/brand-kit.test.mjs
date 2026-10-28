import assert from "node:assert/strict";
import { test } from "node:test";
import { loadModule, samplePost, webFile } from "./helpers/load-module.mjs";

test("brand sections map guides to the kit's four colours or the neutral planning section", async () => {
  const { BRAND_SECTIONS, sectionForPost, groupBySection } = await loadModule(
    "lib/brand-sections.ts",
  );
  assert.deepEqual(
    BRAND_SECTIONS.map((section) => section.id),
    ["visas", "money", "transport", "planning", "living"],
  );
  const post = (slug, domain_slug = "tourism") => ({
    ...samplePost,
    id: slug,
    slug,
    domain_slug,
  });
  assert.equal(
    sectionForPost(post("uzbekistan-visa-requirements", "immigration")).id,
    "visas",
  );
  assert.equal(
    sectionForPost(post("uzbekistan-tourist-registration", "immigration")).id,
    "visas",
  );
  assert.equal(sectionForPost(post("uzbekistan-packing-list")).id, "visas");
  assert.equal(sectionForPost(post("money-in-uzbekistan")).id, "money");
  assert.equal(sectionForPost(post("uzbekistan-trip-cost")).id, "money");
  assert.equal(
    sectionForPost(post("getting-around-uzbekistan")).id,
    "transport",
  );
  assert.equal(sectionForPost(post("arriving-in-tashkent")).id, "transport");
  assert.equal(
    sectionForPost(post("what-to-eat-in-uzbekistan")).id,
    "planning",
  );
  assert.equal(
    sectionForPost(post("renting-a-flat", "everyday-living")).id,
    "living",
  );
  assert.equal(sectionForPost(post("clinics", "healthcare")).id, "living");

  const groups = groupBySection([
    post("money-in-uzbekistan"),
    post("uzbekistan-visa-requirements", "immigration"),
    post("is-uzbekistan-safe"),
  ]);
  assert.deepEqual(
    groups.map((group) => [group.section.id, group.posts.length]),
    [
      ["visas", 1],
      ["money", 1],
      ["transport", 0],
      ["planning", 1],
      ["living", 0],
    ],
  );
});

test("the mosaic parser keeps every tessera, its fill and its order", async () => {
  const { parseMosaic } = await loadModule("lib/anor-mosaic.ts");
  const svg = await webFile("public/brand/anor-mosaic.svg");
  const mosaic = parseMosaic(svg);
  assert.equal(mosaic.viewBox, "0 0 256 256");
  assert.equal(mosaic.tiles.length, 311);
  assert.deepEqual(mosaic.tiles[0], {
    kind: "circle",
    cx: 122,
    cy: 136,
    r: 94.5,
    fill: "#E4D5B4",
  });
  assert.equal(mosaic.tiles[1].kind, "path");
  assert.match(mosaic.tiles[1].d, /^M166\.5,63\.2/);
  assert.equal(mosaic.tiles.at(-1).fill, "#FFC233");
  assert.ok(
    mosaic.tiles.every((tile) => /^#[0-9A-F]{6}$/.test(tile.fill)),
    "every tile has a hex fill",
  );
});

test("the web icons from the kit are installed at the paths the manifest expects", async () => {
  const manifest = JSON.parse(await webFile("public/site.webmanifest"));
  assert.equal(manifest.name, "Uzbekistan OS");
  for (const icon of manifest.icons) {
    await webFile(`public${icon.src}`);
  }
  await webFile("public/favicon.svg");
  await webFile("public/apple-touch-icon.png");
  const layout = await webFile("app/layout.tsx");
  assert.match(layout, /site\.webmanifest/);
  assert.match(layout, /apple-touch-icon\.png/);
  assert.match(layout, /themeColor:\s*"#F8F6F1"/);
});

test("the preview page uses the kit: Inter only, the Anor mark, one primary button per screen", async () => {
  const page = await webFile("app/preview/page.tsx");
  const css = await webFile("app/preview/preview.module.css");
  assert.match(page, /AnorMosaic/);
  assert.match(page, /brand\/anor-horizontal\.svg/);
  assert.match(page, /robots: \{ index: false/);
  assert.doesNotMatch(css, /instrument|fraunces|georgia/i);
  assert.match(css, /--font-sans: var\(--font-inter\)/);
  assert.match(css, /--font-inter/);
  assert.match(css, /#C8102E/i);
  assert.doesNotMatch(page, /[–—]/, "no dashes in visible copy");
  assert.doesNotMatch(
    css,
    /text-transform:\s*uppercase[^}]*\}\s*\.section(Title|Heading)/,
  );
});
