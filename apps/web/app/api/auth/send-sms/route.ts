import { randomUUID } from "node:crypto";
import { sendDevSmsOtp } from "@/lib/devsms";
import { Webhook } from "standardwebhooks";
import { z } from "zod";

export const runtime = "nodejs";
export const maxDuration = 5;

const sendSmsHookSchema = z.object({
  user: z.object({
    id: z.string().uuid(),
    phone: z.string().min(1),
  }),
  sms: z.object({
    otp: z.string().regex(/^\d{4,8}$/),
  }),
});

function hookError(httpCode: number, message: string, status = httpCode) {
  return Response.json({ error: { http_code: httpCode, message } }, { status });
}

export async function POST(request: Request) {
  const requestId = request.headers.get("x-request-id") || randomUUID();
  const payload = await request.text();
  const configuredSecret = process.env.SUPABASE_SEND_SMS_HOOK_SECRET?.trim();
  if (!configuredSecret) {
    console.error("sms_hook_configuration_error", { requestId });
    return hookError(503, "SMS delivery is not configured");
  }

  const secret = configuredSecret.replace(/^v1,whsec_/, "");
  let event: unknown;
  try {
    event = new Webhook(secret).verify(
      payload,
      Object.fromEntries(request.headers),
    );
  } catch {
    console.warn("sms_hook_verification_failed", { requestId });
    return hookError(401, "Invalid webhook signature", 401);
  }

  const parsed = sendSmsHookSchema.safeParse(event);
  if (!parsed.success) {
    console.warn("sms_hook_invalid_payload", { requestId });
    return hookError(400, "Invalid SMS request");
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3_500);
    try {
      const result = await sendDevSmsOtp(
        parsed.data.user.phone,
        parsed.data.sms.otp,
        { signal: controller.signal },
      );
      console.info("sms_hook_delivery_accepted", {
        requestId,
        provider: "devsms",
        providerRequestId: result.data?.request_id,
        parts: result.data?.parts_count,
        reportedCost: result.data?.total_cost,
      });
      return Response.json({});
    } finally {
      clearTimeout(timeout);
    }
  } catch (error) {
    console.error("sms_hook_delivery_failed", {
      requestId,
      category: "provider",
      error: error instanceof Error ? error.message : "UnknownError",
    });
    return hookError(502, "Unable to deliver verification code", 502);
  }
}
