import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("the editorial studio is admin-only and excluded from search indexes", async () => {
  const page = await webFile("app/admin/content/page.tsx");

  assert.match(page, /getStaffIdentity\(\)/);
  assert.match(page, /identity\?\.role !== "admin"/);
  assert.match(page, /redirect\("\/account"\)/);
  assert.match(page, /robots: \{ index: false, follow: false \}/);
});

test("the editorial studio exposes the complete reviewed publication workflow", async () => {
  const [studio, account] = await Promise.all([
    webFile("app/admin/content/content-studio.tsx"),
    webFile("app/account/page.tsx"),
  ]);

  assert.match(studio, /\/admin\/content\/authors/);
  assert.match(studio, /\/admin\/content\/posts\?limit=100/);
  assert.match(
    studio,
    /\/admin\/content\/revisions\/\$\{detail\.revision\.id\}\/submit/,
  );
  assert.match(
    studio,
    /\/admin\/content\/revisions\/\$\{detail\.revision\.id\}\/decision/,
  );
  assert.match(
    studio,
    /\/admin\/content\/revisions\/\$\{detail\.revision\.id\}\/publish/,
  );
  assert.match(studio, /Internal review reason/);
  assert.match(studio, /Request changes/);
  assert.match(studio, /Approve revision/);
  assert.match(studio, /Publish post/);
  assert.match(account, /href="\/admin\/content"/);
});

test("content drafts carry SEO, structured data, author, and evidence fields", async () => {
  const studio = await webFile("app/admin/content/content-studio.tsx");

  assert.match(studio, /SEO title/);
  assert.match(studio, /Meta description/);
  assert.match(studio, /Canonical URL/);
  assert.match(studio, /Hero image alt text/);
  assert.match(studio, /Structured data for search and LLM extraction/);
  assert.match(
    studio,
    /Every citation must select a current reviewed knowledge publication and locator/,
  );
  assert.match(studio, /Guides require at least one approved official source/);
  assert.match(studio, /\/admin\/content\/reviewed-sources\?limit=200/);
  assert.match(studio, /document_version_id: selected\.document_version_id/);
  assert.match(studio, /sources: draft\.citations\.map/);
  assert.match(studio, /Reviewed knowledge sources/);
  assert.match(studio, /Add translation/);
  assert.match(studio, /translation_group_id: draft\.translationGroupId/);
  assert.match(studio, /Creating a localized edition/);
  assert.match(studio, /Language editions/);
  assert.match(studio, /own review and publication\s+decision/);
  assert.match(studio, /Include in assistant retrieval \(RAG\)/);
  assert.match(studio, /include_in_rag: draft\.includeInRag/);
  assert.match(studio, /Default is excluded/);
  assert.match(studio, /Manual reviewed corrections remain higher priority/);
  assert.match(
    studio,
    /Every published post identifies[\s\S]*responsible human[\s\S]*author/,
  );
});
