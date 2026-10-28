import sharp from "sharp";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { hasTrustedOrigin, declaredBodyTooLarge } from "@/lib/request-guards";
import {
  createRequestContext,
  logEvent,
  requestHeaders,
} from "@/lib/monitoring";

export const runtime = "nodejs";
export const maxDuration = 30;
const maximumBytes = 3 * 1024 * 1024;

export async function POST(request: Request) {
  const context = createRequestContext(request, "/api/admin/content/images");
  const headers = requestHeaders(context);
  if (!hasTrustedOrigin(request))
    return Response.json({ error: "Forbidden" }, { status: 403, headers });
  if (declaredBodyTooLarge(request, maximumBytes))
    return Response.json(
      { error: "Images must be 3 MB or smaller." },
      { status: 413, headers },
    );
  if (
    !["image/jpeg", "image/png", "image/webp"].includes(
      request.headers.get("content-type") ?? "",
    )
  )
    return Response.json(
      { error: "Choose a JPEG, PNG, or WebP image." },
      { status: 415, headers },
    );
  const { data } = await (await createClient()).auth.getSession();
  if (!data.session)
    return Response.json(
      { error: "Sign in to upload images." },
      { status: 401, headers },
    );
  const base = (
    process.env.GROUNDED_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");
  const authorization = await fetch(`${base}/admin/content/media-access`, {
    headers: {
      authorization: `Bearer ${data.session.access_token}`,
      "x-request-id": context.requestId,
    },
    cache: "no-store",
  });
  if (!authorization.ok)
    return Response.json(
      { error: "Image upload permission is required." },
      { status: authorization.status, headers },
    );
  const { data: identity } = (await authorization.json()) as {
    data: { principal_id: string };
  };
  const reader = request.body?.getReader();
  if (!reader)
    return Response.json(
      { error: "Choose an image." },
      { status: 400, headers },
    );
  const chunks: Uint8Array[] = [];
  let length = 0;
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    length += chunk.value.byteLength;
    if (length > maximumBytes) {
      await reader.cancel();
      return Response.json(
        { error: "Images must be 3 MB or smaller." },
        { status: 413, headers },
      );
    }
    chunks.push(chunk.value);
  }
  let image: Buffer;
  try {
    image = await sharp(Buffer.concat(chunks), {
      limitInputPixels: 20_000_000,
      animated: false,
    })
      .rotate()
      .resize({
        width: 2400,
        height: 2400,
        fit: "inside",
        withoutEnlargement: true,
      })
      .webp({ quality: 85 })
      .toBuffer();
  } catch {
    return Response.json(
      {
        error:
          "This image could not be decoded. Try a JPEG, PNG, or WebP under 20 megapixels.",
      },
      { status: 422, headers },
    );
  }
  const storage = createAdminClient().storage.from("blog-images");
  const path = `${identity.principal_id}/${crypto.randomUUID()}.webp`;
  const { error } = await storage.upload(path, image, {
    contentType: "image/webp",
    cacheControl: "31536000",
    upsert: false,
  });
  if (error) {
    logEvent("error", "editorial_image_upload_failed", context, {
      status: 503,
    });
    return Response.json(
      { error: "Image storage is unavailable. Please retry." },
      { status: 503, headers },
    );
  }
  logEvent("info", "editorial_image_uploaded", context, { status: 201 });
  return Response.json(
    { url: storage.getPublicUrl(path).data.publicUrl },
    { status: 201, headers },
  );
}
