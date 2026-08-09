import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const pageSource = readFileSync(`${webRoot}/app/page.tsx`, "utf8");
const signupSource = readFileSync(`${webRoot}/app/signup/page.tsx`, "utf8");

test("landing page leads with visa discovery and arrival compliance", () => {
  for (const copy of [
    "Find the right visa",
    "for Uzbekistan",
    "Choose your visa route",
    "Visa-free entry",
    "Electronic visa",
    "Consular visa",
    "Your visa is only part of staying legally",
    "Do not wait until departure to resolve an overstay",
  ]) {
    assert.match(pageSource, new RegExp(copy.replace(/[&.]/g, "\\$&")));
  }
});

test("primary calls to action lead to account creation", () => {
  assert.match(pageSource, /Create free account/);
  assert.match(pageSource, /Sign up and build my plan/);
  assert.ok((pageSource.match(/href="\/signup"/g) ?? []).length >= 3);
});

test("personalized workspace explains the complete visa plan", () => {
  for (const copy of [
    "Your exact visa route",
    "Complete document checklist",
    "Application process",
    "Processing time",
    "Fees and validity",
    "Arrival requirements",
  ]) {
    assert.match(pageSource, new RegExp(copy));
  }
});

test("signup screen is transparent while secure authentication is pending", () => {
  assert.match(signupSource, /Create your free account/);
  assert.match(signupSource, /No personal\s+details are being collected/);
  assert.match(signupSource, /disabled/);
});

test("landing page exposes every official non-electronic visa category", () => {
  const codes = [
    "D-1",
    "D-2",
    "DT",
    "Official",
    "S-1",
    "S-2",
    "S-3",
    "B-1",
    "B-2",
    "J-1",
    "J-2",
    "T",
    "TG",
    "PLG",
    "PV-1",
    "PV-2",
    "VTD",
    "Work",
    "STD",
    "A-1",
    "A-2",
    "A-3",
    "Medical",
    "C-1",
    "C-2",
    "TRAN",
    "EXIT",
    "INV",
  ];

  for (const code of codes) {
    assert.equal(pageSource.includes(`"${code}"`), true, code);
  }
});

test("landing page links only to official visa and foreigner service portals", () => {
  assert.match(pageSource, /https:\/\/www\.e-visa\.gov\.uz\//);
  assert.match(pageSource, /https:\/\/gov\.uz\/en\/mfa\/activity_page/);
  assert.match(pageSource, /https:\/\/my\.gov\.uz\/kaa\/for-foreigners/);
  assert.doesNotMatch(pageSource, /visarun|advantour|wikipedia|facebook/);
});

test("landing page keeps the approved visual assets local", () => {
  const assetNames = [
    "hero-background.avif",
    "feature-official.svg",
    "feature-ai.svg",
    "feature-time.svg",
    "feature-private.svg",
    "category-immigration.png",
    "category-business.png",
    "category-employment.png",
    "category-education.png",
    "category-immigration.svg",
    "category-business.svg",
    "category-employment.svg",
    "category-education.svg",
    "verified.svg",
  ];

  for (const assetName of assetNames) {
    assert.equal(
      existsSync(`${webRoot}/public/landing/${assetName}`),
      true,
      assetName,
    );
  }
});
