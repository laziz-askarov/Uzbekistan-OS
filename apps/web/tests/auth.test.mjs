import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

test("phone auth accepts international numbers and upgrades anonymous accounts", async () => {
  const form = await readFile(
    new URL("app/signup/auth-form.tsx", webRoot),
    "utf8",
  );
  assert.match(form, /\^\\\+\[1-9\]\\d\{7,14\}\$/);
  assert.match(form, /`\+998\$\{compact\}`/);
  assert.match(form, /international country code/);
  assert.match(form, /signInAnonymously/);
  assert.match(form, /updateUser\(\{ phone: nextPhone \}\)/);
  assert.match(form, /type: mode === "create" \? "phone_change" : "sms"/);
  assert.match(form, /shouldCreateUser: false/);
  assert.match(form, /No password, PINFL, or passport number required/);
  assert.doesNotMatch(form, /type="password"/);
  assert.doesNotMatch(form, /Continue with Google|Continue with Apple/);
});

test("server auth uses cookie sessions and verified user lookup", async () => {
  const server = await readFile(
    new URL("lib/supabase/server.ts", webRoot),
    "utf8",
  );
  const proxy = await readFile(
    new URL("lib/supabase/proxy.ts", webRoot),
    "utf8",
  );
  const account = await readFile(
    new URL("app/account/page.tsx", webRoot),
    "utf8",
  );
  assert.match(server, /createServerClient/);
  assert.match(server, /cookieStore\.getAll/);
  assert.match(proxy, /auth\.getClaims\(\)/);
  assert.match(account, /auth\.getUser\(\)/);
  assert.doesNotMatch(proxy, /auth\.getSession\(\)/);
});

test("RLS migration isolates workspace data and protects identity level", async () => {
  const migration = await readFile(
    new URL(
      "../../supabase/migrations/202608100001_progressive_accounts.sql",
      webRoot,
    ),
    "utf8",
  );
  assert.match(migration, /enable row level security/g);
  assert.match(migration, /\(select auth\.uid\(\)\) = owner_id/g);
  assert.match(migration, /identity_level between 0 and 3/);
  assert.match(
    migration,
    /revoke all privileges on public\.profiles from anon, authenticated/,
  );
  assert.match(
    migration,
    /grant update \(display_name, preferred_language, nationality, resident_status\)/,
  );
});
