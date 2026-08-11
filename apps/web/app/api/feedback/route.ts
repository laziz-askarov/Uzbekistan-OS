import { NextResponse } from "next/server";
import { z } from "zod";
import {
  createRequestContext,
  logEvent,
  requestHeaders,
  safeErrorName,
} from "@/lib/monitoring";
import {
  acceptsJson,
  hasTrustedOrigin,
  readLimitedText,
  RequestBodyTooLargeError,
} from "@/lib/request-guards";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const maxDuration = 15;

const maximumBodyBytes = 2 * 1024;
const feedbackSchema = z.object({
  conversationId: z.uuid(),
  messageId: z.uuid(),
  category: z.enum(["incorrect", "outdated", "unclear", "other"]),
  details: z.string().trim().min(1).max(1200).nullable(),
});

function responseHeaders(context: ReturnType<typeof createRequestContext>) {
  return requestHeaders(context, { "cache-control": "no-store" });
}

export async function POST(request: Request) {
  const context = createRequestContext(request, "/api/feedback");
  logEvent("info", "guidance_feedback_started", context, { method: "POST" });

  try {
    if (!hasTrustedOrigin(request)) {
      logEvent("warning", "guidance_feedback_rejected", context, {
        outcome: "untrusted_origin",
        status: 403,
      });
      return NextResponse.json(
        { error: "forbidden" },
        { status: 403, headers: responseHeaders(context) },
      );
    }
    if (!acceptsJson(request)) {
      logEvent("warning", "guidance_feedback_rejected", context, {
        outcome: "unsupported_media_type",
        status: 415,
      });
      return NextResponse.json(
        {
          error: "unsupported_media_type",
          message: "Send feedback as application/json.",
        },
        { status: 415, headers: responseHeaders(context) },
      );
    }

    let rawPayload: string;
    try {
      rawPayload = await readLimitedText(request, maximumBodyBytes);
    } catch (error) {
      if (!(error instanceof RequestBodyTooLargeError)) throw error;
      logEvent("warning", "guidance_feedback_rejected", context, {
        outcome: "payload_too_large",
        status: 413,
      });
      return NextResponse.json(
        {
          error: "payload_too_large",
          message: "Feedback details must be 1,200 characters or fewer.",
        },
        { status: 413, headers: responseHeaders(context) },
      );
    }

    const supabase = await createClient();
    const { data, error: authenticationError } = await supabase.auth.getUser();
    if (authenticationError || !data.user || data.user.is_anonymous) {
      logEvent("warning", "guidance_feedback_rejected", context, {
        outcome: "authentication_required",
        status: 401,
      });
      return NextResponse.json(
        {
          error: "authentication_required",
          message: "Sign in to report guidance.",
        },
        { status: 401, headers: responseHeaders(context) },
      );
    }

    let body: unknown;
    try {
      body = JSON.parse(rawPayload) as unknown;
    } catch {
      body = null;
    }
    const feedback = feedbackSchema.safeParse(body);
    if (!feedback.success) {
      logEvent("warning", "guidance_feedback_rejected", context, {
        outcome: "schema_validation_failed",
        status: 400,
      });
      return NextResponse.json(
        {
          error: "invalid_request",
          message: "Choose an issue type and submit valid feedback details.",
        },
        { status: 400, headers: responseHeaders(context) },
      );
    }

    const { data: message, error: messageError } = await supabase
      .from("messages")
      .select("id")
      .eq("id", feedback.data.messageId)
      .eq("conversation_id", feedback.data.conversationId)
      .eq("owner_id", data.user.id)
      .eq("role", "assistant")
      .maybeSingle();
    if (messageError) throw messageError;
    if (!message) {
      logEvent("warning", "guidance_feedback_rejected", context, {
        outcome: "message_not_found",
        status: 404,
      });
      return NextResponse.json(
        {
          error: "message_not_found",
          message: "That assistant response is not available for review.",
        },
        { status: 404, headers: responseHeaders(context) },
      );
    }

    const { error: insertError } = await supabase
      .from("guidance_feedback")
      .insert({
        reporter_id: data.user.id,
        conversation_id: feedback.data.conversationId,
        message_id: feedback.data.messageId,
        category: feedback.data.category,
        details: feedback.data.details,
      });
    if (insertError?.code === "23505") {
      logEvent("info", "guidance_feedback_completed", context, {
        outcome: "already_submitted",
        status: 409,
      });
      return NextResponse.json(
        {
          error: "already_submitted",
          message: "Feedback for this response has already been recorded.",
        },
        { status: 409, headers: responseHeaders(context) },
      );
    }
    if (insertError) throw insertError;

    logEvent("info", "guidance_feedback_completed", context, {
      outcome: "created",
      status: 201,
      category: feedback.data.category,
    });
    return NextResponse.json(
      { data: { recorded: true } },
      { status: 201, headers: responseHeaders(context) },
    );
  } catch (error) {
    logEvent("error", "guidance_feedback_failed", context, {
      status: 503,
      error: safeErrorName(error),
    });
    return NextResponse.json(
      {
        error: "feedback_unavailable",
        message: "Feedback could not be recorded. Please try again.",
      },
      { status: 503, headers: responseHeaders(context) },
    );
  }
}
