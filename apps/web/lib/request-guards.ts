export class RequestBodyTooLargeError extends Error {
  constructor() {
    super("Request body is too large");
    this.name = "RequestBodyTooLargeError";
  }
}

export function declaredBodyTooLarge(request: Request, maximumBytes: number) {
  const value = request.headers.get("content-length");
  if (!value) return false;
  const length = Number(value);
  return Number.isFinite(length) && length > maximumBytes;
}

export async function readLimitedText(request: Request, maximumBytes: number) {
  if (declaredBodyTooLarge(request, maximumBytes)) {
    throw new RequestBodyTooLargeError();
  }
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > maximumBytes) {
    throw new RequestBodyTooLargeError();
  }
  return text;
}

export function acceptsJson(request: Request) {
  return request.headers
    .get("content-type")
    ?.toLowerCase()
    .startsWith("application/json");
}

export function hasTrustedOrigin(request: Request) {
  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") {
    return false;
  }
  return !origin || origin === new URL(request.url).origin;
}
