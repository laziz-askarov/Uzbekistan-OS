import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

test("email auth sends passwordless links and upgrades anonymous accounts", async () => {
  const form = await readFile(
    new URL("app/signup/auth-form.tsx", webRoot),
    "utf8",
  );
  assert.match(form, /type="email"/);
  assert.match(form, /Continue with email/);
  assert.match(form, /emailRedirectTo/);
  assert.match(form, /signInAnonymously/);
  assert.match(form, /\{ email: nextEmail \}/);
  assert.match(form, /supabase\.auth\.updateUser/);
  assert.match(form, /shouldCreateUser: false/);
  assert.match(form, /No password, PINFL, or passport number required/);
  assert.doesNotMatch(form, /type="password"/);
  assert.doesNotMatch(form, /Continue with phone/);
  assert.doesNotMatch(form, /Continue with Google|Continue with Apple/);
});

test("auth inputs keep readable text and Safari autofill colors", async () => {
  const styles = await readFile(new URL("app/globals.css", webRoot), "utf8");
  assert.match(styles, /\.auth-input-field input,/);
  assert.match(styles, /color: #0f172a;/);
  assert.match(styles, /-webkit-text-fill-color: #0f172a;/);
  assert.match(styles, /input:-webkit-autofill/);
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

test("browser Supabase config uses statically analyzable public variables", async () => {
  const config = await readFile(
    new URL("lib/supabase/config.ts", webRoot),
    "utf8",
  );
  assert.match(config, /process\.env\.NEXT_PUBLIC_SUPABASE_URL/);
  assert.match(config, /process\.env\.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY/);
  assert.doesNotMatch(config, /process\.env\[variable\]/);
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

test("verified email confirmation raises the server-controlled identity level", async () => {
  const migration = await readFile(
    new URL(
      "../../supabase/migrations/202608110004_email_verified_identity.sql",
      webRoot,
    ),
    "utf8",
  );
  assert.match(migration, /new\.email_confirmed_at is not null then 2/);
  assert.match(
    migration,
    /update of phone, email, phone_confirmed_at, email_confirmed_at/,
  );
  assert.match(migration, /security definer set search_path = ''/);
});
