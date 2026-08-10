import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const workspaceUrl = new URL("../app/chat/chat-workspace.tsx", import.meta.url);
const pageUrl = new URL("../app/chat/page.tsx", import.meta.url);
const apiUrl = new URL("../app/api/chat/route.ts", import.meta.url);
const aiUrl = new URL("../lib/visa-ai.ts", import.meta.url);
const workflowsUrl = new URL("../lib/visa-workflows.ts", import.meta.url);
const knowledgeUrl = new URL("../lib/visa-knowledge.json", import.meta.url);

test("chat route renders the internal visa workspace", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(page, /<ChatWorkspace \/>/);
  assert.match(page, /Visa Assistant \| Uzbekistan OS/);
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
  const ai = await readFile(aiUrl, "utf8");
  assert.match(workspace, /fetch\("\/api\/chat"/);
  assert.match(workspace, /active\.messages[\s\S]*?\.slice\(-23\)/);
  assert.match(workspace, /MessageResponse/);
  assert.match(api, /chatRequestSchema\.safeParse/);
  assert.match(api, /x-request-id/);
  assert.match(ai, /\.max\(24\)/);
});

test("chat starts with a clean conversation instead of a seeded visa workflow", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  assert.match(workspace, /title: "New conversation", messages: \[\]/);
  assert.doesNotMatch(workspace, /Show me the electronic visa guide/);
  assert.doesNotMatch(workspace, /eVisaGuide/);
});

test("visa GPT calls use the direct server-side OpenAI provider", async () => {
  const ai = await readFile(aiUrl, "utf8");
  assert.match(ai, /from "@ai-sdk\/openai"/);
  assert.match(ai, /process\.env\.OPENAI_MODEL_ID/);
  assert.match(ai, /const userContext = messages/);
  assert.match(ai, /selectVisaWorkflow\(userContext\)/);
  assert.match(ai, /evidenceForWorkflow\(workflow, userContext\)/);
  assert.match(ai, /citations\.length === ids\.length[\s\S]*?ids\.length > 0/);
  assert.match(ai, /matched >= requiredMatches/);
  assert.match(ai, /validateProfile\(answer, workflow\)/);
  assert.match(ai, /extractProfile\(workflow, messages\)/);
  assert.match(ai, /return visaAnswerSchema\.parse/);
  assert.match(ai, /\.\.\.profileState/);
  assert.doesNotMatch(ai, /AI_GATEWAY_API_KEY|openai\/gpt-/);
});

test("visa intake retains explicit context and cannot re-ask collected fields", async () => {
  const ai = await readFile(aiUrl, "utf8");
  assert.match(
    ai,
    /Read every message so facts stated earlier remain collected/,
  );
  assert.match(ai, /US citizen/);
  assert.match(ai, /field: "nationality", value: "United States"/);
  assert.match(ai, /An explicit negative answer is still a supplied fact/);
  assert.doesNotMatch(ai, /\|none\|/);
  assert.match(ai, /Never ask for a collected field again/);
  assert.match(ai, /AUTHORITATIVE PROFILE STATE/);
  assert.match(ai, /workflow\.requiredProfile\.filter/);
  assert.match(ai, /questionForMissingField\(nextMissingField\)/);
  assert.match(ai, /What nationality is shown in your passport/);
});

test("visa intake gathers one detail at a time before starting the workflow", async () => {
  const ai = await readFile(aiUrl, "utf8");
  const workspace = await readFile(workspaceUrl, "utf8");
  assert.match(ai, /followUpQuestions: z\.array[\s\S]*\.max\(1\)/);
  assert.match(ai, /ask exactly one short, natural follow-up question/);
  assert.match(ai, /Do not start the plan before intake is complete/);
  assert.match(workspace, /Building your visa profile/);
  assert.match(workspace, /Workflow ready/);
  assert.match(workspace, /result\.answer\.followUpQuestions\[0\]/);
});

test("completed visa guidance uses the designed workflow card presentation", async () => {
  const workspace = await readFile(workspaceUrl, "utf8");
  const ai = await readFile(aiUrl, "utf8");
  assert.match(workspace, /completedSectionOrder/);
  assert.match(workspace, /orderedAnswerSections\(answer\)/);
  assert.match(
    workspace,
    /"Completed visa guidance"[\s\S]*?: "Visa guidance status"/,
  );
  assert.match(workspace, /message\.answer\?\.status === "answered"/);
  assert.match(workspace, /styles\.workflowBanner/);
  assert.match(workspace, /styles\.answerSummary/);
  assert.match(workspace, /styles\.profileSummary/);
  assert.match(workspace, /styles\.generatedSection/);
  assert.match(workspace, /<details className=\{styles\.generatedSection\}/);
  assert.match(workspace, /sectionVisual\(section\.heading\)/);
  assert.match(workspace, /answer\.summaryCitationIds/);
  assert.match(workspace, /styles\.generatedSources/);
  assert.match(workspace, /styles\.sectionCitations/);
  assert.match(workspace, /Sources for \$\{section\.heading\}/);
  assert.match(workspace, /answer\.status === "insufficient"/);
  assert.match(workspace, /message\.sources \?\? \[\]\)\.slice\(0, 3\)/);
  assert.match(
    ai,
    /Route; Fees; Requirements and documents; Application process/,
  );
});

test("informational questions bypass intake while active route discovery retains it", async () => {
  const ai = await readFile(aiUrl, "utf8");
  assert.match(ai, /informationalQuestionPattern/);
  assert.match(ai, /personalizedRoutePattern/);
  assert.match(ai, /intakeIsInProgress\(messages\)/);
  assert.match(ai, /In INFORMATION mode, answer the question immediately/);
  assert.match(
    ai,
    /Do not ask for nationality, passport type, dates, purpose, sponsor, host/,
  );
  assert.match(ai, /requiresPersonalization[\s\S]*?await extractProfile/);
  assert.match(ai, /questionNeedsPersonalization/);
  assert.match(ai, /answer\.status === "insufficient"/);
  assert.match(ai, /openai\.tools\.webSearch/);
  assert.match(ai, /allowedDomains: \[\.\.\.officialSearchDomains\]/);
  assert.match(ai, /Live official web search/);
  assert.ok(
    ai.indexOf("if (informationalQuestionPattern.test(latestQuestion))") <
      ai.indexOf("if (intakeIsInProgress(messages))"),
    "an informational question must interrupt an active intake",
  );
});

test("visa requests are routed through explicit deterministic workflows", async () => {
  const workflows = await readFile(workflowsUrl, "utf8");
  for (const workflow of [
    "visa-route-discovery",
    "visa-free-entry",
    "electronic-visa",
    "consular-visa",
    "business-visa",
    "work-visa",
    "student-visa",
    "family-visit",
    "residence-permit",
    "arrival-registration",
    "overstay-and-exit",
  ]) {
    assert.match(workflows, new RegExp(`\\"${workflow}\\"`));
  }
  assert.match(workflows, /selectVisaWorkflow/);
  assert.match(workflows, /evidenceForWorkflow/);
  assert.match(workflows, /visaKnowledge\.chunks/);
  assert.match(workflows, /sourceSha256/);
});

test("all supplied visa documents are retained in the searchable knowledge index", async () => {
  const knowledge = JSON.parse(await readFile(knowledgeUrl, "utf8"));
  assert.equal(knowledge.sourceCount, 13);
  assert.ok(knowledge.chunkCount >= 13);
  assert.equal(knowledge.chunks.length, knowledge.chunkCount);
  for (const filename of [
    "Business visa.docx",
    "e-visa UZ.docx",
    "Family reunification.docx",
    "LIST_OF_CATEGORIES_OF_ENTRY,_EXIT_AND_TRANSIT_VISAS_NON_ELECTRONIC.docx",
    "Overstay penalties.docx",
    "Passport validity requirements.docx",
    "Permanent Residence (PR) in Uzbekistan.docx",
    "Registration of foreigners.docx",
    "Student visas.docx",
    "Temporary residence permits.docx",
    "Visa categories.docx",
    "Visa to the Republic of Uzbekistan MFA.docx",
    "Visa-free entry to Uzbekistan.docx",
  ]) {
    const source = knowledge.sources.find((item) => item.filename === filename);
    assert.ok(source, filename);
    assert.match(source.sha256, /^[a-f0-9]{64}$/);
  }
});
