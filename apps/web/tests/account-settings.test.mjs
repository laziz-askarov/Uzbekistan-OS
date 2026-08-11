import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);
const repoRoot = new URL("../../..", import.meta.url);

test("account settings expose editable profile and verified contact fields", async () => {
  const page = await readFile(new URL("app/account/page.tsx", webRoot), "utf8");
  const settings = await readFile(
    new URL("app/account/account-settings.tsx", webRoot),
    "utf8",
  );

  assert.match(
    page,
    /first_name, last_name, display_name, nationality, avatar_path/,
  );
  assert.match(settings, />First name</);
  assert.match(settings, />Last name</);
  assert.match(settings, />Nationality</);
  assert.match(settings, />Email</);
  assert.match(settings, />Phone</);
  assert.match(
    settings,
    /display_name: `\$\{cleanFirstName\} \$\{cleanLastName\}`/,
  );
  assert.match(settings, /supabase\.auth\.updateUser/);
  assert.match(settings, /type: "phone_change"/);
});

test("profile images are private, bounded, and owner scoped", async () => {
  const settings = await readFile(
    new URL("app/account/account-settings.tsx", webRoot),
    "utf8",
  );
  const migration = await readFile(
    new URL(
      "supabase/migrations/202608110005_account_profile_settings.sql",
      repoRoot,
    ),
    "utf8",
  );

  assert.match(settings, /file\.size > 2 \* 1024 \* 1024/);
  assert.match(settings, /image\/jpeg,image\/png,image\/webp/);
  assert.match(settings, /\.from\("avatars"\)/g);
  assert.match(settings, /createSignedUrl/);
  assert.doesNotMatch(settings, /getPublicUrl/);
  assert.match(migration, /'avatars',[\s\S]*false,[\s\S]*2097152/);
  assert.match(migration, /avatars_select_own/);
  assert.match(migration, /avatars_insert_own/);
  assert.match(
    migration,
    /name = \(select auth\.uid\(\)\)::text \|\| '\/avatar'/g,
  );
  assert.match(migration, /first_name,[\s\S]*last_name,[\s\S]*avatar_path/);
});

test("password recovery is email based and ends in a protected update form", async () => {
  const settings = await readFile(
    new URL("app/account/account-settings.tsx", webRoot),
    "utf8",
  );
  const page = await readFile(
    new URL("app/account/password/page.tsx", webRoot),
    "utf8",
  );
  const form = await readFile(
    new URL("app/account/password/password-form.tsx", webRoot),
    "utf8",
  );

  assert.match(settings, /resetPasswordForEmail/);
  assert.match(settings, /next=\/account\/password/);
  assert.match(page, /supabase\.auth\.getUser/);
  assert.match(page, /redirect\("\/signup"\)/);
  assert.match(form, /updateUser\(\{ password \}\)/);
  assert.match(form, /minLength=\{8\}/g);
});

test("account contact inputs keep dark text including Safari autofill", async () => {
  const styles = await readFile(new URL("app/globals.css", webRoot), "utf8");
  assert.match(styles, /\.account-inline-form input \{[\s\S]*color: #0f172a;/);
  assert.match(styles, /-webkit-text-fill-color: #0f172a;/);
  assert.match(styles, /\.account-inline-form input:-webkit-autofill/);
});
