import {
  createRequestContext,
  logEvent,
  requestHeaders,
  safeErrorName,
} from "@/lib/monitoring";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import { hasTrustedOrigin } from "@/lib/request-guards";

export const runtime = "nodejs";
export const maxDuration = 15;

export async function DELETE(request: Request) {
  const context = createRequestContext(request, "/api/account");
  logEvent("info", "account_deletion_started", context, { method: "DELETE" });

  if (!hasTrustedOrigin(request)) {
    logEvent("warning", "account_deletion_rejected", context, {
      outcome: "untrusted_origin",
      status: 403,
    });
    return Response.json(
      { error: "forbidden" },
      { status: 403, headers: requestHeaders(context) },
    );
  }

  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (!Number.isFinite(contentLength) || contentLength > 128) {
    logEvent("warning", "account_deletion_rejected", context, {
      outcome: "invalid_confirmation",
      status: 400,
    });
    return Response.json(
      { error: "invalid_confirmation" },
      { status: 400, headers: requestHeaders(context) },
    );
  }
  const bodyText = await request.text();
  if (Buffer.byteLength(bodyText, "utf8") > 128) {
    logEvent("warning", "account_deletion_rejected", context, {
      outcome: "invalid_confirmation",
      status: 400,
    });
    return Response.json(
      { error: "invalid_confirmation" },
      { status: 400, headers: requestHeaders(context) },
    );
  }
  let confirmation: { confirmation?: unknown } | null = null;
  try {
    confirmation = JSON.parse(bodyText) as { confirmation?: unknown };
  } catch {
    // Invalid JSON is handled as a rejected confirmation below.
  }
  if (confirmation?.confirmation !== "DELETE") {
    logEvent("warning", "account_deletion_rejected", context, {
      outcome: "invalid_confirmation",
      status: 400,
    });
    return Response.json(
      { error: "invalid_confirmation" },
      { status: 400, headers: requestHeaders(context) },
    );
  }

  try {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user || data.user.is_anonymous) {
      logEvent("warning", "account_deletion_rejected", context, {
        outcome: "authentication_required",
        status: 401,
      });
      return Response.json(
        { error: "authentication_required" },
        { status: 401, headers: requestHeaders(context) },
      );
    }

    const { data: profile, error: profileError } = await supabase
      .from("profiles")
      .select("avatar_path")
      .eq("user_id", data.user.id)
      .maybeSingle();
    if (profileError) throw profileError;

    if (profile?.avatar_path) {
      const { error: avatarError } = await supabase.storage
        .from("avatars")
        .remove([profile.avatar_path]);
      if (avatarError) throw avatarError;
    }

    const admin = createAdminClient();
    const { error: deletionError } = await admin.auth.admin.deleteUser(
      data.user.id,
      false,
    );
    if (deletionError) throw deletionError;

    await supabase.auth.signOut({ scope: "local" }).catch(() => undefined);
    logEvent("info", "account_deletion_completed", context, {
      status: 200,
      outcome: "deleted",
    });
    return Response.json(
      { data: { deleted: true } },
      {
        headers: requestHeaders(context, {
          "cache-control": "no-store",
          "clear-site-data": '"cache", "cookies", "storage"',
        }),
      },
    );
  } catch (error) {
    logEvent("error", "account_deletion_failed", context, {
      status: 503,
      error: safeErrorName(error),
    });
    return Response.json(
      {
        error: "deletion_unavailable",
        message: "Your account could not be deleted. Please try again.",
      },
      { status: 503, headers: requestHeaders(context) },
    );
  }
}
