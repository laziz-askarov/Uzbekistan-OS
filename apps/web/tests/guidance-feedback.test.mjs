import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);
const repoRoot = new URL("../../..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("guidance reports are authenticated, bounded, and schema validated", async () => {
  const route = await webFile("app/api/feedback/route.ts");

  assert.match(route, /hasTrustedOrigin\(request\)/);
  assert.match(route, /acceptsJson\(request\)/);
  assert.match(route, /readLimitedText\(request, maximumBodyBytes\)/);
  assert.match(route, /supabase\.auth\.getUser\(\)/);
  assert.match(route, /data\.user\.is_anonymous/);
  assert.match(route, /feedbackSchema\.safeParse\(body\)/);
  assert.match(route, /\.max\(1200\)/);
  assert.match(route, /"incorrect", "outdated", "unclear", "other"/);
  assert.match(route, /cache-control": "no-store"/);
});

test("feedback can only reference an owned assistant message", async () => {
  const route = await webFile("app/api/feedback/route.ts");

  assert.match(
    route,
    /\.from\("messages"\)[\s\S]*\.eq\("id", feedback\.data\.messageId\)[\s\S]*\.eq\("conversation_id", feedback\.data\.conversationId\)[\s\S]*\.eq\("owner_id", data\.user\.id\)[\s\S]*\.eq\("role", "assistant"\)/,
  );
  assert.match(route, /\.from\("guidance_feedback"\)[\s\S]*\.insert/);
  assert.match(route, /reporter_id: data\.user\.id/);
  assert.match(route, /insertError\?\.code === "23505"/);
  assert.doesNotMatch(
    route,
    /logEvent\([^)]*(?:feedback\.data\.details|rawPayload)/,
  );
});

test("feedback storage is owner scoped and ready for a future admin queue", async () => {
  const migration = await readFile(
    new URL("supabase/migrations/202608110007_guidance_feedback.sql", repoRoot),
    "utf8",
  );

  assert.match(
    migration,
    /create table if not exists public\.guidance_feedback/,
  );
  assert.match(
    migration,
    /status in \('new', 'reviewing', 'resolved', 'dismissed'\)/,
  );
  assert.match(migration, /admin_notes/);
  assert.match(migration, /reviewed_by/);
  assert.match(migration, /guidance_feedback_status_created_idx/);
  assert.match(migration, /guidance_feedback_insert_own/);
  assert.match(migration, /drop policy if exists/);
  assert.match(migration, /\(select auth\.uid\(\)\) = reporter_id/);
  assert.match(migration, /message\.role = 'assistant'/);
  assert.match(migration, /guidance_feedback\.message_id/);
  assert.match(migration, /guidance_feedback\.conversation_id/);
  assert.match(migration, /unique \(reporter_id, message_id\)/);
  assert.match(migration, /message_id uuid[\s\S]*on delete cascade/);
  assert.match(migration, /revoke all privileges[\s\S]*anon, authenticated/);
  assert.match(migration, /grant insert \(reporter_id/);
  assert.doesNotMatch(migration, /grant select[\s\S]*authenticated/);
});

test("every persisted assistant response exposes accessible report controls", async () => {
  const workspace = await webFile("app/chat/chat-workspace.tsx");

  assert.match(workspace, /Report incorrect or outdated guidance/);
  assert.match(workspace, /aria-controls=\{formId\}/);
  assert.match(workspace, /aria-expanded=\{open\}/);
  assert.match(workspace, /What should we review\?/);
  assert.match(workspace, /maxLength=\{1200\}/);
  assert.match(workspace, /fetch\("\/api\/feedback"/);
  assert.match(workspace, /"x-request-id": crypto\.randomUUID\(\)/);
  assert.match(workspace, /message\.role === "assistant"/);
  assert.match(workspace, /message\.persisted !== false/);
  assert.match(workspace, /added to the review queue/);
});

test("account export and privacy disclosures include guidance reports", async () => {
  const [exportRoute, privacy, settings] = await Promise.all([
    webFile("app/api/account/export/route.ts"),
    webFile("app/privacy/page.tsx"),
    webFile("app/account/account-settings.tsx"),
  ]);

  assert.match(exportRoute, /\.from\("guidance_feedback"\)/);
  assert.match(exportRoute, /\.eq\("reporter_id", data\.user\.id\)/);
  assert.match(exportRoute, /guidance_feedback: guidanceFeedback/);
  assert.match(privacy, /incorrect, outdated, or\s+unclear guidance/);
  assert.match(privacy, /related guidance reports/);
  assert.match(settings, /checklists, guidance reports/);
});
