import {
  createRequestContext,
  logEvent,
  requestHeaders,
} from "@/lib/monitoring";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const maxDuration = 30;

const PAGE_SIZE = 500;

type QueryClient = Awaited<ReturnType<typeof createClient>>;

async function fetchAllRows(
  supabase: QueryClient,
  table: "profiles" | "conversations" | "messages" | "checklists",
  columns: string,
  orderColumn: string,
) {
  const rows: unknown[] = [];
  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await supabase
      .from(table)
      .select(columns)
      .order(orderColumn, { ascending: true })
      .range(from, from + PAGE_SIZE - 1);
    if (error) throw error;
    rows.push(...(data ?? []));
    if (!data || data.length < PAGE_SIZE) return rows;
  }
}

export async function GET(request: Request) {
  const context = createRequestContext(request, "/api/account/export");
  logEvent("info", "account_export_started", context, { method: "GET" });

  try {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user || data.user.is_anonymous) {
      logEvent("warning", "account_export_rejected", context, {
        outcome: "authentication_required",
        status: 401,
      });
      return Response.json(
        { error: "authentication_required" },
        { status: 401, headers: requestHeaders(context) },
      );
    }

    const [profiles, conversations, messages, checklists] = await Promise.all([
      fetchAllRows(
        supabase,
        "profiles",
        "user_id,phone,email,display_name,first_name,last_name,preferred_language,nationality,resident_status,identity_level,oneid_user_id,oneid_verified_at,avatar_path,created_at,updated_at",
        "created_at",
      ),
      fetchAllRows(
        supabase,
        "conversations",
        "id,owner_id,title,created_at,updated_at",
        "created_at",
      ),
      fetchAllRows(
        supabase,
        "messages",
        "id,conversation_id,owner_id,role,content,created_at",
        "created_at",
      ),
      fetchAllRows(
        supabase,
        "checklists",
        "id,owner_id,title,items,created_at,updated_at",
        "created_at",
      ),
    ]);

    const profile = profiles[0] as { avatar_path?: string | null } | undefined;
    let avatar: Record<string, unknown> | null = null;
    if (profile?.avatar_path) {
      const { data: avatarBlob, error: avatarError } = await supabase.storage
        .from("avatars")
        .download(profile.avatar_path);
      if (avatarError) throw avatarError;
      avatar = {
        path: profile.avatar_path,
        content_type: avatarBlob.type || "application/octet-stream",
        size_bytes: avatarBlob.size,
        data_base64: Buffer.from(await avatarBlob.arrayBuffer()).toString(
          "base64",
        ),
      };
    }

    const admin = createAdminClient();
    const { data: usageLimits, error: usageError } = await admin
      .from("abuse_rate_limits")
      .select("scope,window_start,request_count,updated_at")
      .eq("user_id", data.user.id)
      .order("window_start", { ascending: true });
    if (usageError) throw usageError;

    const exportedAt = new Date().toISOString();
    const exportData = {
      schema_version: 1,
      exported_at: exportedAt,
      service: "Uzbekistan OS",
      retention:
        "Saved conversations remain until you delete them or delete your account.",
      account: {
        id: data.user.id,
        email: data.user.email ?? null,
        phone: data.user.phone ?? null,
        created_at: data.user.created_at,
        updated_at: data.user.updated_at ?? null,
        last_sign_in_at: data.user.last_sign_in_at ?? null,
        email_confirmed_at: data.user.email_confirmed_at ?? null,
        phone_confirmed_at: data.user.phone_confirmed_at ?? null,
        user_metadata: data.user.user_metadata ?? {},
      },
      profile: profiles[0] ?? null,
      avatar,
      conversations,
      messages,
      checklists,
      usage_limits: usageLimits ?? [],
    };

    logEvent("info", "account_export_completed", context, {
      status: 200,
      conversationCount: conversations.length,
      messageCount: messages.length,
      checklistCount: checklists.length,
      includesAvatar: avatar !== null,
    });

    const date = exportedAt.slice(0, 10);
    return new Response(JSON.stringify(exportData, null, 2), {
      headers: requestHeaders(context, {
        "cache-control": "private, no-store, max-age=0",
        "content-disposition": `attachment; filename="uzbekistan-os-account-export-${date}.json"`,
        "content-type": "application/json; charset=utf-8",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
      }),
    });
  } catch (error) {
    logEvent("error", "account_export_failed", context, {
      status: 503,
      error: error instanceof Error ? error.name : "UnknownError",
    });
    return Response.json(
      {
        error: "export_unavailable",
        message: "Your account export is temporarily unavailable.",
      },
      { status: 503, headers: requestHeaders(context) },
    );
  }
}
