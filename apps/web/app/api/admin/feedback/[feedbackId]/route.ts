import { NextResponse } from "next/server";
import { z } from "zod";
import { getStaffIdentity } from "@/lib/admin-auth";
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

const maximumBodyBytes = 8 * 1024;
const paramsSchema = z.object({ feedbackId: z.uuid() });
const updateSchema = z.object({
  adminNotes: z.string().trim().max(4000).nullable(),
  assignedTo: z.uuid().nullable(),
  status: z.enum(["new", "reviewing", "resolved", "dismissed"]),
});

function responseHeaders(context: ReturnType<typeof createRequestContext>) {
  return requestHeaders(context, { "cache-control": "no-store" });
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ feedbackId: string }> },
) {
  const context = createRequestContext(
    request,
    "/api/admin/feedback/[feedbackId]",
  );
  logEvent("info", "admin_feedback_update_started", context, {
    method: "PATCH",
  });

  try {
    if (!hasTrustedOrigin(request)) {
      return NextResponse.json(
        { error: "forbidden" },
        { status: 403, headers: responseHeaders(context) },
      );
    }
    if (!acceptsJson(request)) {
      return NextResponse.json(
        { error: "unsupported_media_type" },
        { status: 415, headers: responseHeaders(context) },
      );
    }

    const identity = await getStaffIdentity();
    if (!identity) {
      logEvent("warning", "admin_feedback_update_rejected", context, {
        outcome: "staff_authorization_required",
        status: 403,
      });
      return NextResponse.json(
        { error: "staff_authorization_required" },
        { status: 403, headers: responseHeaders(context) },
      );
    }

    const parsedParams = paramsSchema.safeParse(await params);
    if (!parsedParams.success) {
      return NextResponse.json(
        { error: "invalid_feedback_id" },
        { status: 400, headers: responseHeaders(context) },
      );
    }

    let rawBody: string;
    try {
      rawBody = await readLimitedText(request, maximumBodyBytes);
    } catch (error) {
      if (!(error instanceof RequestBodyTooLargeError)) throw error;
      return NextResponse.json(
        { error: "payload_too_large" },
        { status: 413, headers: responseHeaders(context) },
      );
    }
    let body: unknown = null;
    try {
      body = JSON.parse(rawBody) as unknown;
    } catch {
      body = null;
    }
    const update = updateSchema.safeParse(body);
    if (!update.success) {
      return NextResponse.json(
        { error: "invalid_request", message: "Submit a valid review update." },
        { status: 400, headers: responseHeaders(context) },
      );
    }

    const supabase = await createClient();
    const { error } = await supabase.rpc("update_guidance_feedback", {
      p_feedback_id: parsedParams.data.feedbackId,
      p_next_admin_notes: update.data.adminNotes,
      p_next_assigned_to: update.data.assignedTo,
      p_next_status: update.data.status,
      p_request_id: context.requestId,
    });
    if (error) {
      const status =
        error.code === "42501" ? 403 : error.code === "P0002" ? 404 : 400;
      logEvent("warning", "admin_feedback_update_rejected", context, {
        outcome: error.code,
        role: identity.role,
        status,
      });
      return NextResponse.json(
        {
          error:
            status === 403
              ? "forbidden"
              : status === 404
                ? "feedback_not_found"
                : "invalid_update",
          message:
            status === 403
              ? "Your staff role does not permit that change."
              : status === 404
                ? "That report no longer exists."
                : "The review update could not be applied.",
        },
        { status, headers: responseHeaders(context) },
      );
    }

    logEvent("info", "admin_feedback_update_completed", context, {
      role: identity.role,
      status: 200,
      workflowStatus: update.data.status,
    });
    return NextResponse.json(
      { data: { status: update.data.status } },
      { status: 200, headers: responseHeaders(context) },
    );
  } catch (error) {
    logEvent("error", "admin_feedback_update_failed", context, {
      error: safeErrorName(error),
      status: 503,
    });
    return NextResponse.json(
      {
        error: "feedback_admin_unavailable",
        message: "The feedback queue is temporarily unavailable.",
      },
      { status: 503, headers: responseHeaders(context) },
    );
  }
}
