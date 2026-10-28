import assert from "node:assert/strict";
import test from "node:test";
import { loadModule, webFile } from "./helpers/load-module.mjs";

const valid = {
  name: "Jane Traveller",
  email: "jane@example.com",
  travelMonth: "2027-04",
  nights: "10",
  travellers: "2",
  interests: ["architecture", "food"],
  comfort: "comfortable",
  budget: "200-350",
  message: "First trip, interested in Samarkand and Khiva.",
  website: "",
};

test("trip inquiry schema accepts a realistic request and normalizes it for storage", async () => {
  const { parseTripInquiry } = await loadModule("lib/trip-inquiry.ts");
  const result = parseTripInquiry({
    ...valid,
    name: "  Jane Traveller ",
    email: "Jane@Example.com ",
  });
  assert.equal(result.ok, true);
  assert.equal(result.data.name, "Jane Traveller");
  assert.equal(result.data.email, "jane@example.com");
  assert.equal(result.data.nights, 10);
  assert.equal(result.data.travellers, 2);
  assert.deepEqual(result.data.interests, ["architecture", "food"]);
});

test("trip inquiry schema rejects bots, bad contacts and oversized text", async () => {
  const { parseTripInquiry } = await loadModule("lib/trip-inquiry.ts");
  for (const [label, payload] of [
    ["honeypot", { ...valid, website: "http://spam.example" }],
    ["email", { ...valid, email: "not-an-email" }],
    ["month", { ...valid, travelMonth: "April" }],
    ["nights", { ...valid, nights: "0" }],
    ["travellers", { ...valid, travellers: "99" }],
    ["interest", { ...valid, interests: ["hacking"] }],
    ["message", { ...valid, message: "x".repeat(2001) }],
    ["name", { ...valid, name: "" }],
    ["budget", { ...valid, budget: "unlimited" }],
  ]) {
    assert.equal(parseTripInquiry(payload).ok, false, label);
  }
});

test("trip inquiry options are fixed lists shared by the form and the validator", async () => {
  const { INTERESTS, COMFORT_LEVELS, BUDGET_BANDS } = await loadModule(
    "lib/trip-inquiry.ts",
  );
  assert.ok(INTERESTS.some((item) => item.value === "architecture"));
  assert.ok(COMFORT_LEVELS.some((item) => item.value === "comfortable"));
  assert.ok(BUDGET_BANDS.some((item) => item.value === "200-350"));
  const form = await webFile("app/trips/inquiry-form.tsx");
  assert.match(form, /INTERESTS\.map/);
  assert.match(form, /COMFORT_LEVELS\.map/);
  assert.match(form, /BUDGET_BANDS\.map/);
  assert.match(form, /name="website"/);
  assert.match(form, /autoComplete="off"/);
  assert.doesNotMatch(form, /card number|pay now|cardholder|cvc/i);
  assert.match(form, /no payment is\s+taken/i);
});

test("inquiry route guards origin, size and per-email volume, stores with the admin client and logs no contact details", async () => {
  const route = await webFile("app/api/trips/inquiry/route.ts");
  assert.match(route, /hasTrustedOrigin\(request\)/);
  assert.match(route, /readLimitedText\(request, maximumBodyBytes\)/);
  assert.match(route, /const maximumBodyBytes = 8 \* 1024/);
  assert.match(route, /parseTripInquiry/);
  assert.match(route, /createAdminClient\(\)/);
  assert.match(route, /from\("trip_inquiries"\)/);
  assert.match(route, /status: 201/);
  assert.match(route, /"cache-control": "no-store"/);
  assert.match(route, /dailyInquiriesPerEmail/);
  assert.match(route, /reject\(\s*context,\s*429/);
  assert.doesNotMatch(route, /TURNSTILE_SECRET_KEY|siteverify/);
  assert.doesNotMatch(route, /logEvent\([^)]*\b(email|name|message)\b/);
  assert.doesNotMatch(route, /console\.log/);
});

test("trip inquiries are stored in a locked-down table and reviewed only by staff", async () => {
  const migration = await webFile(
    "../../supabase/migrations/202610280016_trip_inquiries.sql",
  );
  assert.match(migration, /create table public\.trip_inquiries/);
  assert.match(migration, /enable row level security/);
  assert.match(
    migration,
    /revoke all privileges on public\.trip_inquiries from public, anon, authenticated/,
  );
  assert.match(migration, /email text not null/);
  assert.match(migration, /status text not null default 'new'/);
  const admin = await webFile("app/admin/inquiries/page.tsx");
  assert.match(admin, /getStaffIdentity\(\)/);
  assert.match(admin, /redirect\("\/account"\)/);
  assert.match(admin, /robots: \{ index: false, follow: false \}/);
  const privacy = await webFile("app/privacy/page.tsx");
  assert.match(privacy, /trip inquir/i);
  assert.match(privacy, /Kebab Travel/);
});

test("the trips page presents Kebab Travel's planning service with a real sequence and the inquiry form", async () => {
  const page = await webFile("app/trips/page.tsx");
  assert.match(page, /Kebab Travel/);
  assert.match(page, /<InquiryForm/);
  assert.match(page, /<SiteHeader/);
  assert.match(page, /canonical: `\$\{SITE_URL\}\/trips`/);
  assert.doesNotMatch(page, /book now|checkout|add to cart/i);
  assert.match(page, /no payment is taken on this site/i);
});
