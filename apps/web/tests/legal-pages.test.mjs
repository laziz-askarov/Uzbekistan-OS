import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const privacyPath = new URL("../app/privacy/page.tsx", import.meta.url);
const termsPath = new URL("../app/terms/page.tsx", import.meta.url);
const landingPath = new URL("../app/page.tsx", import.meta.url);
const authPath = new URL("../app/signup/auth-form.tsx", import.meta.url);

test("privacy policy reflects the services and data flows in production", async () => {
  const privacy = await readFile(privacyPath, "utf8");

  assert.match(privacy, /EffectiveDate|effectiveDate/);
  assert.match(privacy, /11 August 2026/);
  assert.match(privacy, /Tashkent, Uzbekistan/);
  assert.match(privacy, /info@uzbekistanos\.com/g);
  assert.match(privacy, /Supabase/);
  assert.match(privacy, /OpenAI/);
  assert.match(privacy, /Vercel/);
  assert.match(privacy, /Cloudflare/);
  assert.match(privacy, /Turnstile CAPTCHA/);
  assert.match(privacy, /DevSMS/);
  assert.match(privacy, /saved conversation/i);
  assert.match(privacy, /profile image/i);
  assert.match(privacy, /United States and\s+other countries/);
  assert.match(privacy, /does not claim that localization work is complete/);
  assert.match(privacy, /do not sell personal information/i);
  assert.match(privacy, /PINFL/);
});

test("terms state the independent informational and AI limitations", async () => {
  const terms = await readFile(termsPath, "utf8");

  assert.match(terms, /not a government body/);
  assert.match(terms, /not legal\s+advice|licensed immigration\s+adviser/i);
  assert.match(
    terms,
    /AI-generated guidance can be incomplete, outdated, or wrong/,
  );
  assert.match(terms, /Government portals and officials/);
  assert.match(terms, /laws of the Republic of Uzbekistan/);
  assert.match(terms, /mandatory consumer law/);
  assert.match(terms, /info@uzbekistanos\.com/g);
});

test("public footer and account creation disclose both legal documents", async () => {
  const [landing, auth] = await Promise.all([
    readFile(landingPath, "utf8"),
    readFile(authPath, "utf8"),
  ]);

  for (const source of [landing, auth]) {
    assert.match(source, /href="\/privacy"/);
    assert.match(source, /href="\/terms"/);
    assert.match(source, /Privacy Policy/);
    assert.match(source, /Terms of Use/);
  }
  assert.match(auth, /By creating an account, you agree/);
});
