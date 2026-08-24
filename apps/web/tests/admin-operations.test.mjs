import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("admin operations uses the signed-in session in memory and requires both admin guards", async () => {
  const [page, dashboard, sessionHook] = await Promise.all([
    webFile("app/admin/page.tsx"),
    webFile("app/admin/operations-dashboard.tsx"),
    webFile("lib/admin-api-session.ts"),
  ]);

  assert.match(page, /getStaffIdentity\(\)/);
  assert.match(page, /identity\?\.role !== "admin"/);
  assert.match(page, /redirect\("\/account"\)/);
  assert.match(dashboard, /useAdminApiSession\(\)/);
  assert.match(dashboard, /authorization: `Bearer \$\{bearerToken\}`/);
  assert.match(dashboard, /identity\.roles\.includes\("admin"\)/);
  assert.doesNotMatch(dashboard, /type="password"|tokenInput/);
  assert.match(sessionHook, /supabase\.auth\.getSession\(\)/);
  assert.match(sessionHook, /supabase\.auth\.onAuthStateChange/);
  assert.match(sessionHook, /nextSession\.user\.is_anonymous/);
  assert.doesNotMatch(
    `${dashboard}\n${sessionHook}`,
    /localStorage|sessionStorage|document\.cookie/,
  );
});

test("review operations require a staff session and reuse its short-lived API token", async () => {
  const [page, reviewConsole] = await Promise.all([
    webFile("app/admin/reviews/page.tsx"),
    webFile("app/admin/reviews/review-console.tsx"),
  ]);

  assert.match(page, /getStaffIdentity\(\)/);
  assert.match(page, /if \(!identity\) redirect\("\/account"\)/);
  assert.match(reviewConsole, /useAdminApiSession\(\)/);
  assert.match(reviewConsole, /authorization: `Bearer \$\{bearerToken\}`/);
  assert.doesNotMatch(reviewConsole, /type="password"|tokenInput/);
});

test("admin analytics reports service health, readiness, outcomes, and recent errors", async () => {
  const [page, dashboard] = await Promise.all([
    webFile("app/admin/page.tsx"),
    webFile("app/admin/operations-dashboard.tsx"),
  ]);

  assert.match(page, /robots: \{ index: false, follow: false \}/);
  assert.match(dashboard, /publicRequest<WebHealth>\("\/api\/health"\)/);
  assert.match(
    dashboard,
    /publicRequest<ApiHealth>\(`\$\{API_BASE\}\/health`\)/,
  );
  assert.match(
    dashboard,
    /publicRequest<ApiReadiness>\(`\$\{API_BASE\}\/ready`\)/,
  );
  assert.match(dashboard, /NEXT_PUBLIC_API_BASE_URL is not configured/);
  assert.match(dashboard, /System analytics/);
  assert.match(dashboard, /Operational health/);
  assert.match(dashboard, /Job outcomes/);
  assert.match(dashboard, /Recent incidents/);
  assert.match(dashboard, /No recent ingestion errors/);
  assert.match(dashboard, /role="img"/);
  assert.match(dashboard, /aria-label="Service health"/);
});

test("admin error views do not expose tokens or ingestion idempotency keys", async () => {
  const dashboard = await webFile("app/admin/operations-dashboard.tsx");

  assert.doesNotMatch(dashboard, /<code>\{token\}<\/code>/);
  assert.doesNotMatch(dashboard, /incident\.idempotency_key/);
  assert.match(dashboard, /incident\.error_message/);
  assert.match(dashboard, /incident\.error_code/);
});

test("review publishers can load a bounded JSON candidate for server-side publication", async () => {
  const consoleSource = await webFile("app/admin/reviews/review-console.tsx");

  assert.match(consoleSource, /type="file"/);
  assert.match(consoleSource, /accept="\.json,application\/json"/);
  assert.match(consoleSource, /file\.size > 1024 \* 1024/);
  assert.match(
    consoleSource,
    /parsed\.review_item_id !== selected\?\.review\.id/,
  );
  assert.match(consoleSource, /Validate and publish JSON/);
  assert.match(consoleSource, /Download publication template JSON/);
  assert.match(consoleSource, /Missing or invalid fields:/);
  assert.match(consoleSource, /Invalid publication JSON/);
  assert.match(consoleSource, /request<Publication>\("\/admin\/publications"/);
  assert.match(consoleSource, /freshnessDeadline\(publicationDomain\)/);
});

test("admin evidence uploads accept PDF and JSON and keep publication review gated", async () => {
  const [dashboard, reviewConsole, reviewStyles] = await Promise.all([
    webFile("app/admin/operations-dashboard.tsx"),
    webFile("app/admin/reviews/review-console.tsx"),
    webFile("app/admin/reviews/review-console.module.css"),
  ]);

  assert.match(dashboard, /accept="\.pdf,\.json,application\/pdf,application\/json"/);
  assert.match(dashboard, /PDFs are converted to/);
  assert.match(dashboard, /\/admin\/ingestion\/topics/);
  assert.match(dashboard, /list="knowledge-topics"/);
  assert.match(dashboard, /topic,/);
  assert.match(dashboard, /Choose or create a topic/);
  assert.match(dashboard, /Nothing reaches the assistant until/);
  assert.match(reviewConsole, /Download Markdown/);
  assert.match(
    reviewConsole,
    /Download extraction JSON — not publishable/,
  );
  assert.match(reviewConsole, /topic: artifact\.topic/);
  assert.match(reviewConsole, /ThemeToggle/);
  assert.match(reviewStyles, /background: var\(--color-background\)/);
  assert.doesNotMatch(reviewStyles, /\.documentPanel[^}]*background:\s*white/s);
});

test("admins can add bounded manual sources without expanding crawler scope", async () => {
  const dashboard = await webFile("app/admin/operations-dashboard.tsx");

  assert.match(dashboard, /\+ Add new source/);
  assert.match(dashboard, /request<AdminSource>\("\/admin\/sources"/);
  assert.match(dashboard, /confirmed_official: sourceDraft\.confirmedOfficial/);
  assert.match(dashboard, /Knowledge domains/);
  assert.match(dashboard, /Document languages/);
  assert.match(dashboard, /controlled by the named official/);
  assert.match(dashboard, /New\s+sources cannot run crawlers/);
  assert.match(dashboard, /setUploadSource\(created\)/);
});
