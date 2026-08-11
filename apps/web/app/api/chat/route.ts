import { NextResponse } from "next/server";
import {
  createRequestContext,
  logEvent,
  requestHeaders,
  safeErrorName,
} from "@/lib/monitoring";
import {
  acceptsJson,
  readLimitedText,
  RequestBodyTooLargeError,
} from "@/lib/request-guards";
import { createClient } from "@/lib/supabase/server";
import { chatRequestSchema, generateVisaChatResult } from "@/lib/visa-ai";
import { z } from "zod";

export const runtime = "nodejs";
export const maxDuration = 60;
const maximumBodyBytes = 32 * 1024;
const chatQuotaSchema = z.object({
  allowed: z.boolean(),
  remaining: z.number().int().nonnegative(),
  retry_after_seconds: z.number().int().nonnegative(),
  limit_scope: z.enum(["chat_10_minutes", "chat_day"]).nullable(),
});

export async function POST(request: Request) {
  const context = createRequestContext(request, "/api/chat");
  logEvent("info", "api_request_started", context, { method: "POST" });
  try {
    if (!acceptsJson(request)) {
      logEvent("warning", "api_request_rejected", context, {
        outcome: "unsupported_media_type",
        status: 415,
      });
      return NextResponse.json(
        {
          error: "unsupported_media_type",
          message: "Send the request as application/json.",
        },
        { status: 415, headers: requestHeaders(context) },
      );
    }

    let rawPayload: string;
    try {
      rawPayload = await readLimitedText(request, maximumBodyBytes);
    } catch (error) {
      if (!(error instanceof RequestBodyTooLargeError)) throw error;
      logEvent("warning", "api_request_rejected", context, {
        outcome: "payload_too_large",
        status: 413,
      });
      return NextResponse.json(
        {
          error: "payload_too_large",
          message: "The chat request is too large.",
        },
        { status: 413, headers: requestHeaders(context) },
      );
    }

    const supabase = await createClient();
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user || data.user.is_anonymous) {
      logEvent("warning", "api_request_rejected", context, {
        outcome: "authentication_required",
        status: 401,
      });
      return NextResponse.json(
        {
          error: "authentication_required",
          message: "Sign in to use the visa assistant.",
        },
        { status: 401, headers: requestHeaders(context) },
      );
    }

    let body: unknown;
    try {
      body = JSON.parse(rawPayload) as unknown;
    } catch {
      logEvent("warning", "api_request_rejected", context, {
        outcome: "invalid_json",
        status: 400,
      });
      return NextResponse.json(
        {
          error: "invalid_request",
          message: "Send a valid JSON request.",
        },
        { status: 400, headers: requestHeaders(context) },
      );
    }

    const payload = chatRequestSchema.safeParse(body);
    if (!payload.success) {
      logEvent("warning", "api_request_rejected", context, {
        outcome: "schema_validation_failed",
        status: 400,
      });
      return NextResponse.json(
        {
          error: "invalid_request",
          message: "Send between 1 and 12 valid chat messages.",
        },
        { status: 400, headers: requestHeaders(context) },
      );
    }

    const { data: quota, error: quotaError } = await supabase
      .rpc("consume_chat_quota")
      .single();
    const parsedQuota = chatQuotaSchema.safeParse(quota);
    if (quotaError || !parsedQuota.success) {
      logEvent("error", "chat_quota_unavailable", context, {
        status: 503,
        error: quotaError?.code ?? "InvalidQuotaResult",
      });
      return NextResponse.json(
        {
          error: "chat_unavailable",
          message: "Visa guidance is temporarily unavailable.",
        },
        { status: 503, headers: requestHeaders(context) },
      );
    }
    const quotaResult = parsedQuota.data;
    if (!quotaResult.allowed) {
      const retryAfter = Math.max(1, quotaResult.retry_after_seconds);
      logEvent("warning", "chat_rate_limited", context, {
        status: 429,
        limitScope: quotaResult.limit_scope,
        retryAfterSeconds: retryAfter,
      });
      return NextResponse.json(
        {
          error: "rate_limited",
          message: "You have reached the chat limit. Please try again later.",
        },
        {
          status: 429,
          headers: requestHeaders(context, {
            "retry-after": String(retryAfter),
            "x-ratelimit-remaining": "0",
          }),
        },
      );
    }

    const result = await generateVisaChatResult(payload.data.messages);
    logEvent("info", "api_request_completed", context, {
      status: 200,
      outcome: "success",
      messageCount: payload.data.messages.length,
      workflowId: result.workflow.id,
      answerStatus: result.answer.status,
      generated: result.generated,
    });
    return NextResponse.json(result, {
      headers: requestHeaders(context, {
        "x-ratelimit-remaining": String(quotaResult.remaining),
      }),
    });
  } catch (error) {
    logEvent("error", "api_request_failed", context, {
      status: 503,
      error: safeErrorName(error),
    });
    return NextResponse.json(
      {
        error: "chat_unavailable",
        message: "Visa guidance is temporarily unavailable.",
      },
      { status: 503, headers: requestHeaders(context) },
    );
  }
}
