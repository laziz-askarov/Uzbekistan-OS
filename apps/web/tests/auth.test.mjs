import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

test("email and international phone registration use passwords", async () => {
  const form = await readFile(
    new URL("app/signup/auth-form.tsx", webRoot),
    "utf8",
  );
  const inputs = await readFile(new URL("lib/auth-inputs.ts", webRoot), "utf8");
  assert.match(form, /type="email"/);
  assert.match(form, /type="password"/g);
  assert.match(form, /minLength=\{8\}/g);
  assert.match(form, /emailRedirectTo/);
  assert.match(form, /normalizeInternationalPhone/);
  assert.match(inputs, /\^\\\+\[1-9\]\\d\{7,14\}\$/);
  assert.match(form, /supabase\.auth\.verifyOtp/);
  assert.match(form, /supabase\.auth\.signUp/g);
  assert.match(form, /supabase\.auth\.signInWithPassword/g);
  assert.match(form, /channel: "sms"/);
  assert.match(form, /resetPasswordForEmail/);
  assert.match(form, /Forgot password\? Recover by email/);
  assert.match(form, /Already have an account\? Sign in/g);
  assert.match(form, /No PINFL or passport number required/);
  assert.doesNotMatch(form, /auth-tabs|signInAnonymously|signInWithOtp/);
  assert.doesNotMatch(form, /Continue with Google|Continue with Apple/);
});

test("account authentication sends single-use Turnstile tokens to Supabase", async () => {
  const form = await readFile(
    new URL("app/signup/auth-form.tsx", webRoot),
    "utf8",
  );
  const widget = await readFile(
    new URL("components/turnstile-widget.tsx", webRoot),
    "utf8",
  );
  const exampleEnvironment = await readFile(
    new URL(".env.example", webRoot),
    "utf8",
  );

  assert.match(form, /process\.env\.NEXT_PUBLIC_TURNSTILE_SITE_KEY/);
  assert.match(form, /captchaToken/g);
  assert.match(form, /resetCaptcha\(\)/g);
  assert.match(form, /resetPasswordForEmail/);
  assert.match(widget, /next\/script/);
  assert.match(widget, /render=explicit/);
  assert.match(widget, /action: "account_auth"/);
  assert.match(widget, /"expired-callback"/);
  assert.match(widget, /turnstile\.remove/);
  assert.match(exampleEnvironment, /NEXT_PUBLIC_TURNSTILE_SITE_KEY=/);
  assert.doesNotMatch(exampleEnvironment, /TURNSTILE_SECRET_KEY/);
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

test("chat page and API reject missing or anonymous accounts", async () => {
  const page = await readFile(new URL("app/chat/page.tsx", webRoot), "utf8");
  const api = await readFile(new URL("app/api/chat/route.ts", webRoot), "utf8");
  const signup = await readFile(
    new URL("app/signup/page.tsx", webRoot),
    "utf8",
  );
  assert.match(page, /!data\.user \|\| data\.user\.is_anonymous/);
  assert.match(page, /redirect\("\/signup"\)/);
  assert.match(api, /authentication_required/);
  assert.match(api, /status: 401/);
  assert.doesNotMatch(signup, /Continue as guest/);
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
