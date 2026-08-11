import { randomUUID } from "node:crypto";

type LogLevel = "info" | "warning" | "error";
type LogValue = string | number | boolean | null | undefined;

export type RequestContext = {
  requestId: string;
  platformRequestId: string | null;
  route: string;
  startedAt: number;
};

const safeRequestId = /^[a-zA-Z0-9._:-]{1,128}$/;

function cleanRequestId(value: string | null) {
  return value && safeRequestId.test(value) ? value : null;
}

export function createRequestContext(request: Request, route: string) {
  return {
    requestId:
      cleanRequestId(request.headers.get("x-request-id")) ?? randomUUID(),
    platformRequestId: cleanRequestId(request.headers.get("x-vercel-id")),
    route,
    startedAt: Date.now(),
  } satisfies RequestContext;
}

export function requestHeaders(
  context: RequestContext,
  extra: Record<string, string> = {},
) {
  return { "x-request-id": context.requestId, ...extra };
}

export function logEvent(
  level: LogLevel,
  event: string,
  context: RequestContext,
  fields: Record<string, LogValue> = {},
) {
  const payload = JSON.stringify({
    level,
    event,
    route: context.route,
    requestId: context.requestId,
    platformRequestId: context.platformRequestId,
    durationMs: Date.now() - context.startedAt,
    ...fields,
  });
  if (level === "error") console.error(payload);
  else if (level === "warning") console.warn(payload);
  else console.info(payload);
}

export function safeErrorName(error: unknown) {
  return error instanceof Error ? error.name : "UnknownError";
}
