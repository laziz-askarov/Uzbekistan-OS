import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);
const repoRoot = new URL("../../..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("staff roles are server controlled and added to access tokens by a restricted hook", async () => {
  const migration = await readFile(
    new URL(
      "supabase/migrations/202608120009_admin_feedback_rbac.sql",
      repoRoot,
    ),
    "utf8",
  );

  assert.match(
    migration,
    /create type public\.app_role as enum \('admin', 'reviewer'\)/,
  );
  assert.match(migration, /create table public\.user_roles/);
  assert.match(migration, /create table public\.role_permissions/);
  assert.match(migration, /custom_access_token_hook\(event jsonb\)/);
  assert.match(migration, /claims := claims - 'user_role'/);
  assert.match(
    migration,
    /grant execute on function public\.custom_access_token_hook\(jsonb\)[\s\S]*to supabase_auth_admin/,
  );
  assert.match(
    migration,
    /revoke all privileges on public\.user_roles from public, anon, authenticated/,
  );
  assert.match(
    migration,
    /revoke all privileges on public\.role_permissions from public, anon, authenticated/,
  );
  assert.match(migration, /role_permissions_migration_controlled/);
  assert.match(migration, /Role permissions are migration controlled/);
  assert.doesNotMatch(
    migration,
    /grant (?:insert|update|delete)[\s\S]*user_roles[\s\S]*authenticated/,
  );
});

test("authorization checks the signed token claim and the current database role", async () => {
  const [migration, authorization] = await Promise.all([
    readFile(
      new URL(
        "supabase/migrations/202608120009_admin_feedback_rbac.sql",
        repoRoot,
      ),
      "utf8",
    ),
    webFile("lib/admin-auth.ts"),
  ]);

  assert.match(migration, /create or replace function public\.authorize/);
  assert.match(migration, /assigned_role\.user_id = \(select auth\.uid\(\)\)/);
  assert.match(
    migration,
    /assigned_role\.role::text = \(select auth\.jwt\(\) ->> 'user_role'\)/,
  );
  assert.match(authorization, /supabase\.auth\.getClaims\(\)/);
  assert.match(authorization, /getStaffIdentity = cache\([\s\S]*async/);
  assert.match(authorization, /\.from\("user_roles"\)/);
  assert.match(authorization, /assignedRole\?\.role !== role/);
});

test("feedback visibility is scoped by role and assignment", async () => {
  const [migration, feedbackData] = await Promise.all([
    readFile(
      new URL(
        "supabase/migrations/202608120009_admin_feedback_rbac.sql",
        repoRoot,
      ),
      "utf8",
    ),
    webFile("lib/admin-feedback.ts"),
  ]);

  assert.match(migration, /guidance_feedback_staff_select/);
  assert.match(migration, /public\.authorize\('feedback\.read'\)/);
  assert.match(migration, /assigned_to = \(select auth\.uid\(\)\)/);
  assert.match(feedbackData, /identity\.role === "reviewer"/);
  assert.match(
    feedbackData,
    /query = query\.eq\("assigned_to", identity\.userId\)/,
  );
  assert.doesNotMatch(
    feedbackData,
    /reporter:\s*\{[\s\S]{0,140}(?:email|phone):/,
  );
});

test("feedback changes and their audit entry are committed by one database function", async () => {
  const migration = await readFile(
    new URL(
      "supabase/migrations/202608120009_admin_feedback_rbac.sql",
      repoRoot,
    ),
    "utf8",
  );

  assert.match(migration, /create table public\.admin_audit_log/);
  assert.match(migration, /create trigger admin_audit_log_immutable/);
  assert.match(
    migration,
    /raise exception 'Admin audit records are immutable'/,
  );
  assert.match(
    migration,
    /create or replace function public\.update_guidance_feedback/,
  );
  assert.match(migration, /where id = p_feedback_id[\s\S]*for update/);
  assert.match(
    migration,
    /actor_user_role = 'reviewer'[\s\S]*before_record\.assigned_to is distinct from actor_user_id[\s\S]*before_record\.status in \('resolved', 'dismissed'\)/,
  );
  assert.match(migration, /public\.authorize\('feedback\.reopen'\)/);
  assert.match(migration, /Resolution notes are required/);
  assert.match(
    migration,
    /when p_next_status in \('resolved', 'dismissed'\) then before_record\.reviewed_by/,
  );
  assert.match(
    migration,
    /update public\.guidance_feedback[\s\S]*insert into public\.admin_audit_log/,
  );
  assert.match(migration, /'feedback\.assigned'[\s\S]*'feedback\.reopened'/);
  assert.match(migration, /'admin_notes_changed'/);
  assert.doesNotMatch(
    migration,
    /jsonb_build_object\([\s\S]{0,700}'admin_notes',/,
  );
  assert.doesNotMatch(migration, /before_state[\s\S]{0,500}'details'/);
});

test("admin feedback updates are bounded, origin checked, authorized, and request traced", async () => {
  const route = await webFile("app/api/admin/feedback/[feedbackId]/route.ts");

  assert.match(route, /hasTrustedOrigin\(request\)/);
  assert.match(route, /acceptsJson\(request\)/);
  assert.match(route, /readLimitedText\(request, maximumBodyBytes\)/);
  assert.match(route, /getStaffIdentity\(\)/);
  assert.match(route, /\.max\(4000\)/);
  assert.match(route, /supabase\.rpc\("update_guidance_feedback"/);
  assert.match(route, /p_request_id: context\.requestId/);
  assert.match(route, /admin_feedback_update_completed/);
  assert.match(route, /\{ data: \{ status: update\.data\.status \} \}/);
  assert.doesNotMatch(route, /logEvent\([^)]*(?:adminNotes|assignedTo)/);
});

test("the protected dashboard supports all requested filters and workflow actions", async () => {
  const [page, dashboard, account] = await Promise.all([
    webFile("app/admin/feedback/page.tsx"),
    webFile("app/admin/feedback/feedback-dashboard.tsx"),
    webFile("app/account/page.tsx"),
  ]);

  assert.match(page, /getStaffIdentity\(\)/);
  assert.match(page, /if \(!identity\) redirect\("\/account"\)/);
  assert.match(page, /listFeedbackForStaff\(identity, filters\)/);
  assert.match(
    dashboard,
    /const feedbackCategories = \[[\s\S]*"incorrect"[\s\S]*"outdated"[\s\S]*"unclear"[\s\S]*"other"[\s\S]*\] as const/,
  );
  assert.match(dashboard, /name="status"/);
  assert.match(dashboard, /name="from"[\s\S]{0,80}type="date"/);
  assert.match(dashboard, /name="to"[\s\S]{0,80}type="date"/);
  assert.match(dashboard, /Assigned reviewer/);
  assert.match(dashboard, /Internal notes/);
  assert.match(dashboard, /updateReport\("resolved"\)/);
  assert.match(dashboard, /updateReport\("reviewing"\)[\s\S]*Reopen report/);
  assert.match(dashboard, /aria-live="polite"/);
  assert.match(account, /getStaffIdentity\(\)/);
  assert.match(account, /staffIdentity[\s\S]*href="\/admin\/feedback"/);
});
