import { z } from "zod";
import type { StaffIdentity, StaffRole } from "@/lib/admin-auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export const feedbackCategories = [
  "incorrect",
  "outdated",
  "unclear",
  "other",
] as const;
export const feedbackStatuses = [
  "new",
  "reviewing",
  "resolved",
  "dismissed",
] as const;

export type FeedbackCategory = (typeof feedbackCategories)[number];
export type FeedbackStatus = (typeof feedbackStatuses)[number];

export type FeedbackFilters = {
  category: FeedbackCategory | null;
  dateFrom: string | null;
  dateTo: string | null;
  page: number;
  status: FeedbackStatus | null;
};

export type StaffOption = {
  email: string | null;
  name: string | null;
  role: StaffRole;
  userId: string;
};

export type FeedbackItem = {
  adminNotes: string | null;
  assignee: StaffOption | null;
  category: FeedbackCategory;
  conversationId: string;
  createdAt: string;
  details: string | null;
  id: string;
  messageId: string;
  reporter: {
    name: string | null;
    userId: string;
  };
  responseText: string;
  reviewedAt: string | null;
  reviewer: StaffOption | null;
  status: FeedbackStatus;
  updatedAt: string;
};

export type FeedbackPageData = {
  items: FeedbackItem[];
  page: number;
  pageSize: number;
  staff: StaffOption[];
  total: number;
};

const PAGE_SIZE = 30;
const dateSchema = z.iso.date();

export function parseFeedbackFilters(
  input: Record<string, string | string[] | undefined>,
): FeedbackFilters {
  const category = z.enum(feedbackCategories).safeParse(input.category);
  const status = z.enum(feedbackStatuses).safeParse(input.status);
  const dateFrom = dateSchema.safeParse(input.from);
  const dateTo = dateSchema.safeParse(input.to);
  const parsedPage = z.coerce.number().int().min(1).safeParse(input.page);
  return {
    category: category.success ? category.data : null,
    dateFrom: dateFrom.success ? dateFrom.data : null,
    dateTo: dateTo.success ? dateTo.data : null,
    page: parsedPage.success ? parsedPage.data : 1,
    status: status.success ? status.data : null,
  };
}

function nameFromProfile(profile: {
  display_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}) {
  const fullName = [profile.first_name, profile.last_name]
    .filter(Boolean)
    .join(" ")
    .trim();
  return fullName || profile.display_name?.trim() || null;
}

function responseText(content: unknown) {
  if (!content || typeof content !== "object" || Array.isArray(content)) {
    return "Assistant response unavailable.";
  }
  const text = (content as Record<string, unknown>).text;
  return typeof text === "string" && text.trim()
    ? text
    : "Assistant response unavailable.";
}

export async function listFeedbackForStaff(
  identity: StaffIdentity,
  filters: FeedbackFilters,
): Promise<FeedbackPageData> {
  const supabase = await createClient();
  const admin = createAdminClient();
  const from = (filters.page - 1) * PAGE_SIZE;
  let query = supabase
    .from("guidance_feedback")
    .select(
      "id,reporter_id,conversation_id,message_id,category,details,status,admin_notes,assigned_to,reviewed_by,reviewed_at,created_at,updated_at",
      { count: "exact" },
    )
    .order("created_at", { ascending: false })
    .range(from, from + PAGE_SIZE - 1);

  if (identity.role === "reviewer")
    query = query.eq("assigned_to", identity.userId);
  if (filters.category) query = query.eq("category", filters.category);
  if (filters.status) query = query.eq("status", filters.status);
  if (filters.dateFrom)
    query = query.gte("created_at", `${filters.dateFrom}T00:00:00.000Z`);
  if (filters.dateTo) {
    const exclusiveDate = new Date(`${filters.dateTo}T00:00:00.000Z`);
    exclusiveDate.setUTCDate(exclusiveDate.getUTCDate() + 1);
    query = query.lt("created_at", exclusiveDate.toISOString());
  }

  const { data: reports, error: reportError, count } = await query;
  if (reportError) throw reportError;

  const rows = reports ?? [];
  const messageIds = rows.map((item) => item.message_id);
  const userIds = [
    ...new Set(
      rows
        .flatMap((item) => [
          item.reporter_id,
          item.assigned_to,
          item.reviewed_by,
        ])
        .filter((value): value is string => Boolean(value)),
    ),
  ];
  let roleQuery = admin.from("user_roles").select("user_id,role").order("role");
  if (identity.role === "reviewer") {
    roleQuery = roleQuery.eq("user_id", identity.userId);
  }
  const [messageResult, profileResult, roleResult] = await Promise.all([
    messageIds.length
      ? admin.from("messages").select("id,content").in("id", messageIds)
      : Promise.resolve({ data: [], error: null }),
    userIds.length
      ? admin
          .from("profiles")
          .select("user_id,email,display_name,first_name,last_name")
          .in("user_id", userIds)
      : Promise.resolve({ data: [], error: null }),
    roleQuery,
  ]);
  if (messageResult.error) throw messageResult.error;
  if (profileResult.error) throw profileResult.error;
  if (roleResult.error) throw roleResult.error;

  const profiles = new Map(
    (profileResult.data ?? []).map((profile) => [profile.user_id, profile]),
  );
  const messages = new Map(
    (messageResult.data ?? []).map((message) => [message.id, message.content]),
  );
  const roleRows = roleResult.data ?? [];
  const roleMap = new Map(
    roleRows.map((role) => [role.user_id, role.role as StaffRole]),
  );
  const staffIds = roleRows.map((role) => role.user_id);
  const missingStaffIds = staffIds.filter((id) => !profiles.has(id));
  if (missingStaffIds.length) {
    const { data: staffProfiles, error: staffProfileError } = await admin
      .from("profiles")
      .select("user_id,email,display_name,first_name,last_name")
      .in("user_id", missingStaffIds);
    if (staffProfileError) throw staffProfileError;
    for (const profile of staffProfiles ?? [])
      profiles.set(profile.user_id, profile);
  }

  function staffOption(userId: string | null): StaffOption | null {
    if (!userId) return null;
    const role = roleMap.get(userId);
    if (!role) return null;
    const profile = profiles.get(userId);
    return {
      email: profile?.email ?? null,
      name: profile ? nameFromProfile(profile) : null,
      role,
      userId,
    };
  }

  return {
    items: rows.map((report) => {
      const reporter = profiles.get(report.reporter_id);
      return {
        adminNotes: report.admin_notes,
        assignee: staffOption(report.assigned_to),
        category: report.category as FeedbackCategory,
        conversationId: report.conversation_id,
        createdAt: report.created_at,
        details: report.details,
        id: report.id,
        messageId: report.message_id,
        reporter: {
          name: reporter ? nameFromProfile(reporter) : null,
          userId: report.reporter_id,
        },
        responseText: responseText(messages.get(report.message_id)),
        reviewedAt: report.reviewed_at,
        reviewer: staffOption(report.reviewed_by),
        status: report.status as FeedbackStatus,
        updatedAt: report.updated_at,
      };
    }),
    page: filters.page,
    pageSize: PAGE_SIZE,
    staff: staffIds
      .map(staffOption)
      .filter((item): item is StaffOption => Boolean(item)),
    total: count ?? 0,
  };
}
