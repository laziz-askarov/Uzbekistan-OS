import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);
const repoRoot = new URL("../../..", import.meta.url);

test("chat enforces durable account quotas before model generation", async () => {
  const route = await readFile(
    new URL("app/api/chat/route.ts", webRoot),
    "utf8",
  );
  const migration = await readFile(
    new URL("supabase/migrations/202608110006_chat_abuse_limits.sql", repoRoot),
    "utf8",
  );

  assert.match(route, /rpc\("consume_chat_quota"\)/);
  assert.match(route, /chatQuotaSchema\.safeParse\(quota\)/);
  assert.match(route, /if \(!quotaResult\.allowed\)/);
  assert.match(route, /status: 429/);
  assert.match(route, /"retry-after"/);
  assert.match(route, /"x-ratelimit-remaining"/g);
  assert.match(
    migration,
    /create table if not exists public\.abuse_rate_limits/,
  );
  assert.match(migration, /enable row level security/);
  assert.match(
    migration,
    /revoke all privileges[\s\S]*from anon, authenticated/,
  );
  assert.match(migration, /current_user_id uuid := \(select auth\.uid\(\)\)/);
  assert.match(migration, /pg_advisory_xact_lock/);
  assert.match(migration, /short_limit constant integer := 20/);
  assert.match(migration, /daily_limit constant integer := 100/);
  assert.match(migration, /grant execute[\s\S]*to authenticated/);
});

test("public POST routes reject oversized bodies before provider work", async () => {
  const chat = await readFile(
    new URL("app/api/chat/route.ts", webRoot),
    "utf8",
  );
  const sms = await readFile(
    new URL("app/api/auth/send-sms/route.ts", webRoot),
    "utf8",
  );
  const guards = await readFile(
    new URL("lib/request-guards.ts", webRoot),
    "utf8",
  );

  assert.match(chat, /maximumBodyBytes = 32 \* 1024/);
  assert.match(chat, /acceptsJson/);
  assert.match(chat, /status: 413/);
  assert.match(chat, /status: 415/);
  assert.match(sms, /maximumBodyBytes = 16 \* 1024/);
  assert.match(sms, /RequestBodyTooLargeError/);
  assert.match(guards, /content-length/);
  assert.match(guards, /new TextEncoder\(\)\.encode\(text\)\.byteLength/);
});

test("API monitoring is structured, correlated, and excludes sensitive payloads", async () => {
  const monitoring = await readFile(
    new URL("lib/monitoring.ts", webRoot),
    "utf8",
  );
  const chat = await readFile(
    new URL("app/api/chat/route.ts", webRoot),
    "utf8",
  );
  const sms = await readFile(
    new URL("app/api/auth/send-sms/route.ts", webRoot),
    "utf8",
  );
  const health = await readFile(
    new URL("app/api/health/route.ts", webRoot),
    "utf8",
  );

  assert.match(monitoring, /JSON\.stringify/);
  assert.match(monitoring, /x-vercel-id/);
  assert.match(monitoring, /durationMs/);
  assert.match(monitoring, /safeRequestId/);
  assert.match(chat, /api_request_completed/);
  assert.match(sms, /sms_hook_delivery_accepted/);
  assert.match(health, /health_check_completed/);
  assert.match(health, /cache-control/);
  assert.doesNotMatch(chat, /logEvent\([^;]*(?:rawPayload|messages:)/s);
  assert.doesNotMatch(sms, /logEvent\([^;]*(?:phone|otp)/is);
});

test("Vercel analytics and real-user performance monitoring load globally", async () => {
  const layout = await readFile(new URL("app/layout.tsx", webRoot), "utf8");
  const packageJson = JSON.parse(
    await readFile(new URL("package.json", webRoot), "utf8"),
  );

  assert.match(layout, /@vercel\/analytics\/next/);
  assert.match(layout, /@vercel\/speed-insights\/next/);
  assert.match(layout, /<Analytics \/>/);
  assert.match(layout, /<SpeedInsights \/>/);
  assert.ok(packageJson.dependencies["@vercel/analytics"]);
  assert.ok(packageJson.dependencies["@vercel/speed-insights"]);
});
