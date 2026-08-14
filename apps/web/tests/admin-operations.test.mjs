import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);

async function webFile(path) {
  return readFile(new URL(path, webRoot), "utf8");
}

test("admin operations keeps credentials in memory and requires the API admin role", async () => {
  const dashboard = await webFile("app/admin/operations-dashboard.tsx");

  assert.match(dashboard, /type="password"/);
  assert.match(dashboard, /authorization: `Bearer \$\{bearerToken\}`/);
  assert.match(dashboard, /identity\.roles\.includes\("admin"\)/);
  assert.match(dashboard, /setToken\(""\)/);
  assert.doesNotMatch(
    dashboard,
    /localStorage|sessionStorage|document\.cookie/,
  );
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
