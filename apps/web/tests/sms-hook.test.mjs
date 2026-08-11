import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const webRoot = new URL("..", import.meta.url);
const routeUrl = new URL("app/api/auth/send-sms/route.ts", webRoot);
const providerUrl = new URL("lib/eskiz-sms.ts", webRoot);

test("Supabase SMS hook verifies signed requests before sending", async () => {
  const route = await readFile(routeUrl, "utf8");
  assert.match(route, /new Webhook\(secret\)\.verify/);
  assert.match(route, /SUPABASE_SEND_SMS_HOOK_SECRET/);
  assert.match(route, /sendSmsHookSchema\.safeParse/);
  assert.match(route, /AbortController/);
  assert.match(route, /3_500/);
  assert.match(route, /return Response\.json\(\{\}\)/);
  assert.doesNotMatch(
    route,
    /console\.(?:info|warn|error)\([^\n]*(?:phone|otp)/i,
  );
});

test("Eskiz adapter accepts E.164 international numbers and uses universal OTP", async () => {
  const provider = await readFile(providerUrl, "utf8");
  assert.match(provider, /\^\\\+\[1-9\]\\d\{7,14\}\$/);
  assert.match(provider, /return compact\.slice\(1\)/);
  assert.match(provider, /type: "universal_otp"/);
  assert.match(provider, /template_type: 1/);
  assert.match(provider, /ESKIZ_SMS_API_TOKEN/);
  assert.match(provider, /https:\/\/devsms\.uz\/api\/send_sms\.php/);
  assert.doesNotMatch(provider, /NEXT_PUBLIC_ESKIZ/);
  assert.doesNotMatch(provider, /Only valid \+998/);
});
