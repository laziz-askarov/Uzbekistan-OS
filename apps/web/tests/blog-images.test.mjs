import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import sharp from "sharp";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";

const require = createRequire(import.meta.url);
async function load(path, mocks = {}, fetcher = globalThis.fetch) {
  const source = await readFile(new URL(`../${path}`, import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText;
  const loaded = { exports: {} };
  new Function("require", "module", "exports", "fetch", output)(
    (name) => mocks[name] ?? require(name),
    loaded,
    loaded.exports,
    fetcher,
  );
  return loaded.exports;
}

async function fixture({ session = true, authorized = true } = {}) {
  const uploads = [];
  let authorizationCalls = 0;
  const guards = await load("lib/request-guards.ts");
  const route = await load(
    "app/api/admin/content/images/route.ts",
    {
      "@/lib/request-guards": guards,
      "@/lib/monitoring": {
        createRequestContext: () => ({ requestId: "image-test" }),
        requestHeaders: () => ({ "x-request-id": "image-test" }),
        logEvent() {},
      },
      "@/lib/supabase/server": {
        createClient: async () => ({
          auth: {
            getSession: async () => ({
              data: { session: session ? { access_token: "test-only" } : null },
            }),
          },
        }),
      },
      "@/lib/supabase/admin": {
        createAdminClient: () => ({
          storage: {
            from: (bucket) => {
              assert.equal(bucket, "blog-images");
              return {
                upload: async (...args) => {
                  uploads.push(args);
                  return { error: null };
                },
                getPublicUrl: (path) => ({
                  data: { publicUrl: `https://media.example/${path}` },
                }),
              };
            },
          },
        }),
      },
    },
    async (url, init) => {
      authorizationCalls++;
      assert.match(url, /\/admin\/content\/media-access$/);
      assert.equal(init.headers["x-request-id"], "image-test");
      return Response.json(
        { data: { principal_id: "writer-123" } },
        { status: authorized ? 200 : 403 },
      );
    },
  );
  return { ...route, uploads, calls: () => authorizationCalls };
}
function request(body, headers = {}) {
  return new Request("https://www.uzbekistanos.com/api/admin/content/images", {
    method: "POST",
    headers: {
      origin: "https://www.uzbekistanos.com",
      "content-type": "image/png",
      ...headers,
    },
    body,
  });
}

test("editorial images require API permission and are converted to bounded WebP", async () => {
  const route = await fixture();
  const png = await sharp({
    create: { width: 20, height: 10, channels: 3, background: "red" },
  })
    .png()
    .toBuffer();
  const response = await route.POST(request(png));
  assert.equal(response.status, 201);
  assert.equal(route.calls(), 1);
  assert.equal(route.uploads.length, 1);
  const [path, buffer, options] = route.uploads[0];
  assert.match(path, /^writer-123\/[\w-]+\.webp$/);
  assert.equal(options.upsert, false);
  const metadata = await sharp(buffer).metadata();
  assert.equal(metadata.format, "webp");
  assert.equal(metadata.width, 20);
  assert.equal(metadata.exif, undefined);
  assert.match((await response.json()).url, /^https:\/\/media.example\//);
});

test("image uploads reject foreign origins, oversized bodies and SVG", async () => {
  for (const [headers, status] of [
    [{ origin: "https://attacker.example" }, 403],
    [{ "content-length": String(3 * 1024 * 1024 + 1) }, 413],
    [{ "content-type": "image/svg+xml" }, 415],
  ]) {
    const route = await fixture();
    assert.equal(
      (await route.POST(request("invalid", headers))).status,
      status,
    );
    assert.equal(route.calls(), 0);
    assert.equal(route.uploads.length, 0);
  }
});

test("signed-out users, revoked writers and invalid images cannot upload", async () => {
  for (const [settings, status] of [
    [{ session: false }, 401],
    [{ authorized: false }, 403],
    [{}, 422],
  ]) {
    const route = await fixture(settings);
    assert.equal((await route.POST(request("not-an-image"))).status, status);
    assert.equal(route.uploads.length, 0);
  }
});

test("chunked image bodies are bounded even without Content-Length", async () => {
  const route = await fixture();
  const response = await route.POST(
    request(new Uint8Array(3 * 1024 * 1024 + 1)),
  );
  assert.equal(response.status, 413);
  assert.equal(route.uploads.length, 0);
});

test("article image Markdown renders safely and preserves alternate text", async () => {
  const { MarkdownContent } = await load(
    "components/editorial/markdown-content.tsx",
  );
  const html = renderToStaticMarkup(
    createElement(MarkdownContent, {
      markdown:
        "Before\n\n![Samarkand square](https://images.example/square.webp)\n\nAfter\n\n![Bad](javascript:alert)\n\n<script>bad()</script>",
    }),
  );
  assert.match(html, /<img[^>]+alt="Samarkand square"/);
  assert.match(html, /loading="lazy"/);
  assert.doesNotMatch(html, /src="javascript:/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /<p>After<\/p>/);
});

test("public blog cache expires only after API-authorized publication succeeds", async () => {
  for (const apiStatus of [200, 403, 409]) {
    const expirations = [];
    const refreshedPaths = [];
    const guards = await load("lib/request-guards.ts");
    const { POST } = await load(
      "app/api/admin/content/publish/route.ts",
      {
        "next/cache": {
          revalidateTag: (...args) => expirations.push(args),
          revalidatePath: (path) => refreshedPaths.push(path),
        },
        "@/lib/request-guards": guards,
        "@/lib/monitoring": {
          createRequestContext: () => ({ requestId: "publish-test" }),
          requestHeaders: () => ({ "x-request-id": "publish-test" }),
        },
        "@/lib/supabase/server": {
          createClient: async () => ({
            auth: {
              getSession: async () => ({
                data: { session: { access_token: "test-only" } },
              }),
            },
          }),
        },
      },
      async (url, init) => {
        assert.match(
          url,
          /\/revisions\/00000000-0000-4000-8000-000000000001\/publish-now$/,
        );
        assert.equal(init.headers["x-request-id"], "publish-test");
        return Response.json(
          { data: { id: "revision" } },
          { status: apiStatus },
        );
      },
    );
    const response = await POST(
      new Request("https://www.uzbekistanos.com/api/admin/content/publish", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          revisionId: "00000000-0000-4000-8000-000000000001",
          instant: true,
        }),
      }),
    );
    assert.equal(response.status, apiStatus);
    assert.deepEqual(
      refreshedPaths,
      apiStatus === 200
        ? [
            "/",
            "/blog",
            "/sitemap.xml",
            "/llms.txt",
            "/llms-full.txt",
            "/blog/rss.xml",
          ]
        : [],
    );
    assert.deepEqual(
      expirations,
      apiStatus === 200 ? [["editorial-content", { expire: 0 }]] : [],
    );
  }
});

test("sitemap discovers the first publication after an empty launch", async () => {
  let posts = [];
  const { default: sitemap, dynamic } = await load("app/sitemap.ts", {
    "@/lib/editorial-content": {
      SITE_URL: "https://www.uzbekistanos.com",
      publicPostUrl: (slug) => `https://www.uzbekistanos.com/blog/${slug}`,
      listPublishedPosts: async () => posts,
    },
  });
  assert.equal(dynamic, "force-dynamic");
  assert.equal((await sitemap()).length, 4);
  posts = [
    {
      slug: "first-visit",
      translation_group_id: "first-group",
      language_code: "en",
      updated_at: "2026-10-27T21:00:00Z",
      hero_image_url: "https://images.example/first.webp",
    },
  ];
  const entry = (await sitemap()).find((item) =>
    item.url.endsWith("/blog/first-visit"),
  );
  assert.ok(entry);
  assert.deepEqual(entry.images, ["https://images.example/first.webp"]);
  assert.equal(entry.alternates.languages.en, entry.url);
});
