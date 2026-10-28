import { NextResponse } from "next/server";
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
import { createAdminClient } from "@/lib/supabase/admin";
import { parseTripInquiry } from "@/lib/trip-inquiry";

export const runtime = "nodejs";
export const maxDuration = 15;

const maximumBodyBytes = 8 * 1024;
const dailyInquiriesPerEmail = 5;

function responseHeaders(
  context: ReturnType<typeof createRequestContext>,
  additional: Record<string, string> = {},
) {
  return requestHeaders(context, { "cache-control": "no-store", ...additional });
}

function reject(
  context: ReturnType<typeof createRequestContext>,
  status: number,
  outcome: string,
  error: string,
  message: string,
) {
  logEvent("warning", "trip_inquiry_rejected", context, { outcome, status });
  return NextResponse.json(
    { error, message },
    { status, headers: responseHeaders(context) },
  );
}

export async function POST(request: Request) {
  const context = createRequestContext(request, "/api/trips/inquiry");
  logEvent("info", "trip_inquiry_started", context, { method: "POST" });

  try {
    if (!hasTrustedOrigin(request)) {
      return reject(context, 403, "untrusted_origin", "forbidden", "Forbidden.");
    }
    if (!acceptsJson(request)) {
      return reject(
        context,
        415,
        "unsupported_media_type",
        "unsupported_media_type",
        "Send the inquiry as application/json.",
      );
    }

    let rawPayload: string;
    try {
      rawPayload = await readLimitedText(request, maximumBodyBytes);
    } catch (error) {
      if (!(error instanceof RequestBodyTooLargeError)) throw error;
      return reject(
        context,
        413,
        "payload_too_large",
        "payload_too_large",
        "Your message is too long. Keep it under 2,000 characters.",
      );
    }

    let body: unknown;
    try {
      body = JSON.parse(rawPayload) as unknown;
    } catch {
      body = null;
    }
    const parsed = parseTripInquiry(body);
    if (!parsed.ok) {
      return reject(
        context,
        400,
        "schema_validation_failed",
        "invalid_request",
        "Check the highlighted fields and try again.",
      );
    }
    const inquiry = parsed.data;

    const admin = createAdminClient();
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const { count, error: countError } = await admin
      .from("trip_inquiries")
      .select("id", { count: "exact", head: true })
      .eq("email", inquiry.email)
      .gte("created_at", since);
    if (countError) throw countError;
    if ((count ?? 0) >= dailyInquiriesPerEmail) {
      return reject(
        context,
        429,
        "rate_limited",
        "rate_limited",
        "We already have your inquiry. We reply by email within a few days.",
      );
    }

    const { error: insertError } = await admin.from("trip_inquiries").insert({
      name: inquiry.name,
      email: inquiry.email,
      travel_month: inquiry.travelMonth,
      nights: inquiry.nights,
      travellers: inquiry.travellers,
      interests: inquiry.interests,
      comfort: inquiry.comfort,
      budget: inquiry.budget,
      message: inquiry.message,
      source_path: inquiry.sourcePath ?? null,
      request_id: context.requestId,
    });
    if (insertError) throw insertError;

    logEvent("info", "trip_inquiry_completed", context, {
      outcome: "created",
      status: 201,
      travelMonth: inquiry.travelMonth,
      travellers: inquiry.travellers,
    });
    return NextResponse.json(
      { data: { received: true } },
      { status: 201, headers: responseHeaders(context) },
    );
  } catch (error) {
    logEvent("error", "trip_inquiry_failed", context, {
      status: 503,
      error: safeErrorName(error),
    });
    return NextResponse.json(
      {
        error: "inquiry_unavailable",
        message: "We could not record your inquiry. Please try again, or email us directly.",
      },
      { status: 503, headers: responseHeaders(context) },
    );
  }
}
