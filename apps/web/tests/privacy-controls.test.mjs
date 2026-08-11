import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);
const repoRoot = new URL("../../..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("account export is authenticated, complete, paginated, and not cached", async () => {
  const route = await webFile("app/api/account/export/route.ts");

  assert.match(route, /supabase\.auth\.getUser\(\)/);
  assert.match(route, /data\.user\.is_anonymous/);
  assert.match(route, /\.range\(from, from \+ PAGE_SIZE - 1\)/);
  for (const dataset of [
    "profiles",
    "conversations",
    "messages",
    "checklists",
    "abuse_rate_limits",
    "guidance_feedback",
  ]) {
    assert.match(route, new RegExp(`["]${dataset}["]`));
  }
  assert.match(route, /\.eq\("user_id", data\.user\.id\)/);
  assert.match(route, /\.from\("avatars"\)[\s\S]*\.download/);
  assert.match(route, /data_base64/);
  assert.match(route, /content-disposition/);
  assert.match(route, /private, no-store/);
  assert.doesNotMatch(route, /logEvent\([^)]*(?:content|email|phone)/);
});

test("account deletion removes the private avatar before the auth account", async () => {
  const route = await webFile("app/api/account/route.ts");

  assert.match(route, /hasTrustedOrigin\(request\)/);
  assert.match(route, /contentLength > 128/);
  assert.match(route, /Buffer\.byteLength\(bodyText, "utf8"\) > 128/);
  assert.match(route, /confirmation\?\.confirmation !== "DELETE"/);
  assert.match(route, /supabase\.auth\.getUser\(\)/);
  assert.match(route, /data\.user\.is_anonymous/);
  assert.match(route, /\.from\("avatars"\)[\s\S]*\.remove/);
  assert.match(route, /admin\.auth\.admin\.deleteUser/);
  assert.ok(
    route.indexOf('.from("avatars")') <
      route.indexOf("admin.auth.admin.deleteUser"),
    "private avatar removal must happen before deleting the auth owner",
  );
  assert.match(route, /clear-site-data/);
  assert.match(route, /cache-control": "no-store"/);
});

test("database cascades and owner policies cover account and conversation deletion", async () => {
  const accountsMigration = await readFile(
    new URL(
      "supabase/migrations/202608100001_progressive_accounts.sql",
      repoRoot,
    ),
    "utf8",
  );
  const limitsMigration = await readFile(
    new URL("supabase/migrations/202608110006_chat_abuse_limits.sql", repoRoot),
    "utf8",
  );

  assert.match(
    accountsMigration,
    /profiles[\s\S]*references auth\.users\(id\) on delete cascade/,
  );
  assert.match(
    accountsMigration,
    /conversations[\s\S]*references auth\.users\(id\) on delete cascade/,
  );
  assert.match(
    accountsMigration,
    /messages[\s\S]*references public\.conversations\(id\) on delete cascade/,
  );
  assert.match(
    accountsMigration,
    /checklists[\s\S]*references auth\.users\(id\) on delete cascade/,
  );
  assert.match(accountsMigration, /conversations_own_all/);
  assert.match(accountsMigration, /grant select, insert, update, delete/);
  assert.match(
    limitsMigration,
    /references auth\.users\(id\) on delete cascade/,
  );
});

test("users can export or permanently delete their account from settings", async () => {
  const settings = await webFile("app/account/account-settings.tsx");

  assert.match(settings, /href="\/api\/account\/export"/);
  assert.match(settings, /Download account data/);
  assert.match(settings, /deleteConfirmation !== "DELETE"/);
  assert.match(settings, /fetch\("\/api\/account"/);
  assert.match(settings, /method: "DELETE"/);
  assert.match(
    settings,
    /JSON\.stringify\(\{ confirmation: deleteConfirmation \}\)/,
  );
  assert.match(settings, /Delete account permanently/);
  assert.match(settings, /This cannot be[\s\S]*undone/);
});

test("conversation history exposes owner-scoped permanent deletion", async () => {
  const workspace = await webFile("app/chat/chat-workspace.tsx");

  assert.match(workspace, /aria-label={`Delete \$\{chat\.title\}`}/);
  assert.match(workspace, /window\.confirm/);
  assert.match(
    workspace,
    /\.from\("conversations"\)[\s\S]*\.delete\(\)[\s\S]*\.eq\("id", chat\.id\)[\s\S]*\.eq\("owner_id", user\.id\)/,
  );
  assert.match(workspace, /chats\.filter\(\(item\) => item\.id !== chat\.id\)/);
  assert.match(workspace, /This conversation could not be deleted/);
});

test("published policy defines retention, self-service export, and deletion limits", async () => {
  const privacy = await webFile("app/privacy/page.tsx");

  assert.match(
    privacy,
    /Saved conversations do not currently expire automatically/,
  );
  assert.match(
    privacy,
    /until you delete that conversation[\s\S]*delete your account/,
  );
  assert.match(privacy, /download a current JSON export/);
  assert.match(privacy, /provider systems or backups/);
  assert.match(
    privacy,
    /OpenAI API records may remain for up to[\s\S]*30 days/,
  );
});

test("the documented server admin key remains server-only", async () => {
  const envExample = await webFile(".env.example");

  assert.match(envExample, /^SUPABASE_SECRET_KEY=$/m);
  assert.doesNotMatch(envExample, /NEXT_PUBLIC_SUPABASE_SECRET_KEY/);
});
