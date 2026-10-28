import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
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

test("the preview page uses the kit: Inter only, the Anor mark, photographs with credits", async () => {
  const page = await webFile("app/preview/page.tsx");
  const css = await webFile("app/preview/preview.module.css");
  assert.match(page, /AnorMosaic/);
  assert.match(page, /brand\/anor-horizontal\.svg/);
  assert.match(
    page,
    /brand\/anor-mono-white-horizontal\.svg/,
    "white mark over the photograph",
  );
  assert.match(page, /robots: \{ index: false/);
  assert.match(page, /GuideIndex/);
  assert.match(page, /PHOTO_LIST/, "the footer prints every photo credit");
  assert.doesNotMatch(css, /instrument|fraunces|georgia/i);
  assert.match(css, /--font-sans: var\(--font-inter\)/);
  assert.match(css, /#c8102e/i);
  assert.doesNotMatch(
    css,
    /#f8f6f1|#f0ece4|#e6e0d5/i,
    "neutral ground, not the kit's warm paper",
  );
  assert.doesNotMatch(page, /[\u2013\u2014]/, "no dashes in visible copy");
});

test("every editorial photograph is on disk and credited", async () => {
  const { PHOTO_LIST } = await loadModule("lib/photos.ts");
  assert.ok(PHOTO_LIST.length >= 8);
  for (const photo of PHOTO_LIST) {
    const file = await readFile(
      new URL(`../public${photo.src}`, import.meta.url),
    );
    assert.ok(file.length > 20_000, `${photo.src} is a real image`);
    assert.ok(file.length < 900_000, `${photo.src} is under 900 KB`);
    assert.ok(photo.alt.length > 20, `${photo.src} has descriptive alt text`);
    assert.match(photo.credit.license, /^(CC|Public domain)/);
    assert.match(photo.credit.source, /^https:\/\/commons\.wikimedia\.org\//);
    assert.ok(photo.width >= 1200 && photo.height >= 800);
  }
});

test("the guide index shows a photograph for every guide and keeps keyboard access", async () => {
  const React = await import("react");
  const { renderToStaticMarkup } = await import("react-dom/server");
  const { GuideIndex } = await loadModule("components/brand/guide-index.tsx", {
    "next/link": {
      __esModule: true,
      default: (props) => React.createElement("a", props),
    },
  });
  const html = renderToStaticMarkup(
    React.createElement(GuideIndex, {
      groups: [
        {
          id: "visas",
          title: "Visas and documents",
          description: "Entry rules.",
          href: "/travel#before-you-go",
          count: "1 guide",
          guides: [
            {
              slug: "uzbekistan-visa-requirements",
              href: "/blog/uzbekistan-visa-requirements",
              title: "Uzbekistan Visa Requirements",
              verified: "Oct 28, 2026",
              verifiedAt: "2026-10-28T09:00:00Z",
              image: "https://images.example/visa.webp",
              alt: "Shah-i-Zinda",
            },
          ],
        },
      ],
    }),
  );
  assert.match(html, /data-section="visas"/);
  assert.match(html, /href="\/blog\/uzbekistan-visa-requirements"/);
  assert.match(
    html,
    /<img[^>]+src="https:\/\/images.example\/visa.webp"[^>]+alt=""/,
  );
  assert.match(
    html,
    /aria-hidden="true"/,
    "the floating preview is decorative",
  );
  assert.match(
    html,
    /<time dateTime="2026-10-28T09:00:00Z">Oct 28, 2026<\/time>/,
  );
});
