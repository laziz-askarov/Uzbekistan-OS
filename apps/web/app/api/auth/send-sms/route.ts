import { sendDevSmsOtp } from "@/lib/devsms";
import {
  createRequestContext,
  logEvent,
  requestHeaders,
  safeErrorName,
  type RequestContext,
} from "@/lib/monitoring";
import {
  readLimitedText,
  RequestBodyTooLargeError,
} from "@/lib/request-guards";
import { Webhook } from "standardwebhooks";
import { z } from "zod";

export const runtime = "nodejs";
export const maxDuration = 5;
const maximumBodyBytes = 16 * 1024;

const sendSmsHookSchema = z.object({
  user: z.object({
    id: z.string().uuid(),
    phone: z.string().min(1),
  }),
  sms: z.object({
    otp: z.string().regex(/^\d{4,8}$/),
  }),
});

function hookError(
  context: RequestContext,
  httpCode: number,
  message: string,
  status = httpCode,
) {
  return Response.json(
    { error: { http_code: httpCode, message } },
    { status, headers: requestHeaders(context) },
  );
}

export async function POST(request: Request) {
  const context = createRequestContext(request, "/api/auth/send-sms");
  logEvent("info", "api_request_started", context, { method: "POST" });
  let payload: string;
  try {
    payload = await readLimitedText(request, maximumBodyBytes);
  } catch (error) {
    if (!(error instanceof RequestBodyTooLargeError)) {
      logEvent("error", "api_request_failed", context, {
        status: 400,
        error: safeErrorName(error),
      });
      return hookError(context, 400, "Unable to read SMS request", 400);
    }
    logEvent("warning", "api_request_rejected", context, {
      outcome: "payload_too_large",
      status: 413,
    });
    return hookError(context, 413, "SMS request is too large", 413);
  }

  const configuredSecret = process.env.SUPABASE_SEND_SMS_HOOK_SECRET?.trim();
  if (!configuredSecret) {
    logEvent("error", "sms_hook_configuration_error", context, {
      status: 503,
    });
    return hookError(context, 503, "SMS delivery is not configured");
  }

  const secret = configuredSecret.replace(/^v1,whsec_/, "");
  let event: unknown;
  try {
    event = new Webhook(secret).verify(
      payload,
      Object.fromEntries(request.headers),
    );
  } catch {
    logEvent("warning", "sms_hook_verification_failed", context, {
      status: 401,
    });
    return hookError(context, 401, "Invalid webhook signature", 401);
  }

  const parsed = sendSmsHookSchema.safeParse(event);
  if (!parsed.success) {
    logEvent("warning", "sms_hook_invalid_payload", context, { status: 400 });
    return hookError(context, 400, "Invalid SMS request");
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
      logEvent("info", "sms_hook_delivery_accepted", context, {
        status: 200,
        outcome: "success",
        provider: "devsms",
        providerRequestId: result.data?.request_id,
        parts: result.data?.parts_count,
        reportedCost: result.data?.total_cost,
      });
      return Response.json({}, { headers: requestHeaders(context) });
    } finally {
      clearTimeout(timeout);
    }
  } catch (error) {
    logEvent("error", "sms_hook_delivery_failed", context, {
      status: 502,
      category: "provider",
      error: safeErrorName(error),
    });
    return hookError(context, 502, "Unable to deliver verification code", 502);
  }
}
