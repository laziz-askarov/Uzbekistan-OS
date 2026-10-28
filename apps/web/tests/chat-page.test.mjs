import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { z } from "zod";

const workspaceUrl = new URL("../app/chat/chat-workspace.tsx", import.meta.url);
const pageUrl = new URL("../app/chat/page.tsx", import.meta.url);
const apiUrl = new URL("../app/api/chat/route.ts", import.meta.url);
const chatContractUrl = new URL("../lib/chat-contract.ts", import.meta.url);
const postgresUuidUrl = new URL("../lib/postgres-uuid.ts", import.meta.url);

test("chat route renders the internal visa workspace", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(page, /getStaffIdentity\(\)/);
  assert.match(
    page,
    /<ChatWorkspace staffRole=\{staffIdentity\?\.role \?\? null\} \/>/,
  );
  assert.match(page, /Visa Assistant \| Uzbekistan OS/);
});

test("chat navigation exposes ingestion and review tools only to staff", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");

  assert.match(workspace, /staffRole: "admin" \| "reviewer" \| null/);
  assert.match(workspace, /staffRole === "admin"/);
  assert.match(workspace, /href="\/admin"/);
  assert.match(workspace, /href="\/admin\/reviews"/);
  assert.match(workspace, /href="\/admin\/feedback"/);
  assert.match(workspace, /aria-label="Staff tools"/);
});

test("chat workspace identifies grounded GPT guidance and cites official sources", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  assert.match(workspace, /GPT guidance is limited to reviewed evidence/);
  assert.match(workspace, /https:\/\/www\.e-visa\.gov\.uz\//);
  assert.match(workspace, /https:\/\/gov\.uz\/en\/mfa/);
  assert.match(workspace, /MessageResponse/);
  assert.match(workspace, /citedSourceChunks/);
  assert.match(workspace, /source\.sourceFile/);
});

test("chat workspace does not expose out-of-scope agent or appointment actions", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  assert.doesNotMatch(workspace, /Apply via UzOS Visa Agent/);
  assert.doesNotMatch(workspace, /Book a Personal Consultant/);
});

test("chat sends bounded message history to the grounded server endpoint", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  const api = await readFile(apiUrl, "utf8");
  const chatContract = await readFile(chatContractUrl, "utf8");
  const monitoring = await readFile(
    new URL("../lib/monitoring.ts", import.meta.url),
    "utf8",
  );
  assert.match(workspace, /fetch\("\/api\/chat"/);
  assert.match(workspace, /active\.messages[\s\S]*?\.slice\(-23\)/);
  assert.match(workspace, /MessageResponse/);
  assert.match(api, /chatRequestSchema\.safeParse/);
  assert.match(api, /GROUNDED_API_BASE_URL/);
  assert.match(api, /`Bearer \$\{accessToken\}`/);
  assert.match(api, /`\$\{groundedApiBase\}\/assistant\/answer`/);
  assert.match(api, /groundedResponseSchema\.safeParse/);
  assert.match(api, /cache: "no-store"/);
  assert.match(api, /requestHeaders\(context/);
  assert.match(monitoring, /"x-request-id"/);
  assert.match(chatContract, /\.max\(24\)/);
  assert.doesNotMatch(api, /visa-ai|generateVisaChatResult/);
});

test("grounded responses accept deterministic PostgreSQL source UUIDs", async () => {
  const api = await readFile(apiUrl, "utf8");
  const postgresUuid = await readFile(postgresUuidUrl, "utf8");
  const sourceId = "00000000-0000-0000-0000-000000002102";

  assert.equal(z.guid().safeParse(sourceId).success, true);
  assert.match(postgresUuid, /postgresUuidSchema = z\.guid\(\)/);
  assert.match(api, /source_id: postgresUuidSchema/);
  assert.match(api, /grounded_api_response_invalid/);
  assert.match(api, /issue\.path\.join\("\."\)/);
});

test("chat starts with a clean conversation instead of a seeded visa workflow", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  assert.match(workspace, /title: "New conversation", messages: \[\]/);
  assert.doesNotMatch(workspace, /Show me the electronic visa guide/);
  assert.doesNotMatch(workspace, /eVisaGuide/);
});

test("chat requires an account and persists account-owned history", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  const page = await readFile(pageUrl, "utf8");
  assert.doesNotMatch(
    workspace,
    /signInAnonymously|Guest session|Guest access/,
  );
  assert.match(workspace, /Authentication required/);
  assert.match(workspace, /from\("conversations"\)/);
  assert.match(workspace, /from\("messages"\)/);
  assert.match(workspace, /owner_id: user\.id/);
  assert.match(page, /redirect\("\/signup"\)/);
  assert.match(workspace, /href="\/account"/);
  assert.match(workspace, /select\("first_name,last_name"\)/);
  assert.match(workspace, /aria-label="Open account settings"/);
  assert.match(workspace, /<Icon name="gear"/);
  assert.doesNotMatch(workspace, /label: user\.(?:phone|email)/);
  assert.doesNotMatch(workspace, />Manage</);
});
