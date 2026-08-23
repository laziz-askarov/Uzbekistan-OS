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
import { chatRequestSchema } from "@/lib/chat-contract";
import { createClient } from "@/lib/supabase/server";
import { z } from "zod";

export const runtime = "nodejs";
export const maxDuration = 60;
const maximumBodyBytes = 32 * 1024;
const groundedApiBase =
  process.env.GROUNDED_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";
const chatQuotaSchema = z.object({
  allowed: z.boolean(),
  remaining: z.number().int().nonnegative(),
  retry_after_seconds: z.number().int().nonnegative(),
  limit_scope: z.enum(["chat_10_minutes", "chat_day"]).nullable(),
});
const groundedCitationSchema = z.object({
  source_id: z.string().uuid(),
  locator: z.string(),
  quote: z.string().nullable().optional(),
  source_url: z.string().url().nullable().optional(),
  source_title: z.string().nullable().optional(),
  reviewed_at: z.string().nullable().optional(),
});
const groundedResponseSchema = z.object({
  data: z.object({
    answer: z.object({
      status: z.enum(["answered", "needs_clarification", "insufficient"]),
      language: z.enum(["en", "uz", "ru"]),
      summary: z.string(),
      sections: z.array(
        z.object({
          id: z.string(),
          heading: z.string(),
          claims: z.array(
            z.object({
              id: z.string(),
              text: z.string(),
              citations: z.array(
                z.object({ evidence_id: z.string(), quote: z.string() }),
              ),
            }),
          ),
        }),
      ),
      clarification: z.object({ question: z.string() }).nullable().optional(),
    }),
    evidence: z.object({
      items: z.array(
        z.object({
          chunk_id: z.string(),
          title: z.string(),
          heading: z.string(),
          content: z.string(),
          citations: z.array(groundedCitationSchema),
        }),
      ),
    }),
    intent: z.string(),
    accepted: z.boolean(),
    generated: z.boolean(),
  }),
});

function workflowForIntent(intent: string) {
  const title = intent
    .split("_")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
  return {
    id: intent.replaceAll("_", "-"),
    title: title || "Official guidance",
    description: "Grounded in reviewed, currently eligible official evidence.",
  };
}

function toVisaResult(parsed: z.infer<typeof groundedResponseSchema>) {
  const { answer, evidence, intent, accepted, generated } = parsed.data;
  const citationIds = [
    ...new Set(
      answer.sections.flatMap((section) =>
        section.claims.flatMap((claim) =>
          claim.citations.map((citation) => citation.evidence_id),
        ),
      ),
    ),
  ];
  return {
    answer: {
      status:
        answer.status === "needs_clarification"
          ? ("needs_information" as const)
          : answer.status,
      summary: answer.summary,
      summaryCitationIds: answer.status === "answered" ? citationIds : [],
      sections: answer.sections.map((section) => ({
        heading: section.heading,
        content: section.claims.map((claim) => claim.text).join("\n\n"),
        citationIds: [
          ...new Set(
            section.claims.flatMap((claim) =>
              claim.citations.map((citation) => citation.evidence_id),
            ),
          ),
        ],
      })),
      profile: [],
      missingProfileFields: [],
      followUpQuestions: answer.clarification?.question
        ? [answer.clarification.question]
        : [],
    },
    workflow: workflowForIntent(intent),
    sources: evidence.items
      .map((item) => {
        const citation = item.citations.find(
          (candidate) => candidate.source_url,
        );
        return citation?.source_url
          ? {
              id: item.chunk_id,
              title: citation.source_title ?? item.title,
              url: citation.source_url,
              reviewedAt: citation.reviewed_at ?? new Date().toISOString(),
              content: item.content,
              sourceFile: item.heading,
            }
          : null;
      })
      .filter((item) => item !== null),
    generated: generated && accepted,
  };
}

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

    const { data: sessionData, error: sessionError } =
      await supabase.auth.getSession();
    const accessToken = sessionData.session?.access_token;
    if (sessionError || !accessToken) {
      return NextResponse.json(
        {
          error: "authentication_required",
          message: "Sign in again to use the assistant.",
        },
        { status: 401, headers: requestHeaders(context) },
      );
    }
    const groundedResponse = await fetch(
      `${groundedApiBase}/assistant/answer`,
      {
        method: "POST",
        headers: {
          accept: "application/json",
          authorization: `Bearer ${accessToken}`,
          "content-type": "application/json",
          "x-request-id": context.requestId,
        },
        body: JSON.stringify({ messages: payload.data.messages }),
        cache: "no-store",
      },
    );
    if (!groundedResponse.ok) {
      logEvent("error", "grounded_api_failed", context, {
        status: groundedResponse.status,
      });
      return NextResponse.json(
        {
          error: "chat_unavailable",
          message: "Grounded guidance is temporarily unavailable.",
        },
        {
          status:
            groundedResponse.status >= 500 ? 503 : groundedResponse.status,
          headers: requestHeaders(context),
        },
      );
    }
    const groundedPayload = groundedResponseSchema.safeParse(
      await groundedResponse.json(),
    );
    if (!groundedPayload.success) {
      throw new Error("GroundedApiResponseInvalid");
    }
    const result = toVisaResult(groundedPayload.data);
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
