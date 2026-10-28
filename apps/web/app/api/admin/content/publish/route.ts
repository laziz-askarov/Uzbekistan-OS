import { revalidatePath, revalidateTag } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import {
  hasTrustedOrigin,
  readLimitedText,
  RequestBodyTooLargeError,
} from "@/lib/request-guards";
import { createRequestContext, requestHeaders } from "@/lib/monitoring";

export const runtime = "nodejs";
export async function POST(request: Request) {
  const context = createRequestContext(request, "/api/admin/content/publish");
  const headers = requestHeaders(context);
  if (!hasTrustedOrigin(request))
    return Response.json(
      { error: { message: "Forbidden" } },
      { status: 403, headers },
    );
  let payload: { revisionId: string; instant?: boolean };
  try {
    payload = JSON.parse(await readLimitedText(request, 1024));
    if (
      typeof payload.revisionId !== "string" ||
      !/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(
        payload.revisionId,
      ) ||
      (payload.instant !== undefined && typeof payload.instant !== "boolean")
    )
      throw new Error();
  } catch (error) {
    return Response.json(
      { error: { message: "Invalid publish request." } },
      {
        status: error instanceof RequestBodyTooLargeError ? 413 : 400,
        headers,
      },
    );
  }
  const { data } = await (await createClient()).auth.getSession();
  if (!data.session)
    return Response.json(
      { error: { message: "Sign in to publish." } },
      { status: 401, headers },
    );
  const base = (
    process.env.GROUNDED_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");
  const response = await fetch(
    `${base}/admin/content/revisions/${payload.revisionId}/${payload.instant ? "publish-now" : "publish"}`,
    {
      method: "POST",
      headers: {
        authorization: `Bearer ${data.session.access_token}`,
        "x-request-id": context.requestId,
      },
      cache: "no-store",
    },
  );
  const result = await response.json();
  if (response.ok) {
    revalidateTag("editorial-content", { expire: 0 });
    for (const path of [
      "/",
      "/blog",
      "/sitemap.xml",
      "/llms.txt",
      "/llms-full.txt",
      "/blog/rss.xml",
    ]) {
      revalidatePath(path);
    }
  }
  return Response.json(result, { status: response.status, headers });
}
