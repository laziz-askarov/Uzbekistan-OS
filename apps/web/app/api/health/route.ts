import { NextResponse } from "next/server";
import {
  createRequestContext,
  logEvent,
  requestHeaders,
} from "@/lib/monitoring";

export function GET(request: Request) {
  const context = createRequestContext(request, "/api/health");
  logEvent("info", "health_check_completed", context, {
    status: 200,
    outcome: "healthy",
  });
  return NextResponse.json(
    {
      data: {
        service: "web",
        status: "ok",
        version: "0.1.0",
        commit: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) ?? "local",
      },
      meta: { request_id: context.requestId },
    },
    {
      headers: requestHeaders(context, {
        "cache-control": "no-store, max-age=0",
      }),
    },
  );
}
