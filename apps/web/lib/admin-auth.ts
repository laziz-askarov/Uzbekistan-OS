import type { JwtPayload } from "@supabase/supabase-js";
import { cache } from "react";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export const staffRoles = ["admin", "reviewer"] as const;
export type StaffRole = (typeof staffRoles)[number];

export type StaffIdentity = {
  email: string | null;
  role: StaffRole;
  userId: string;
};

function staffRoleFromClaims(claims: JwtPayload): StaffRole | null {
  const value = claims.user_role;
  return value === "admin" || value === "reviewer" ? value : null;
}

export const getStaffIdentity = cache(
  async (): Promise<StaffIdentity | null> => {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.getClaims();
    if (error || !data?.claims || data.claims.is_anonymous) return null;

    const role = staffRoleFromClaims(data.claims);
    if (!role) return null;
    const admin = createAdminClient();
    const { data: assignedRole, error: roleError } = await admin
      .from("user_roles")
      .select("role")
      .eq("user_id", data.claims.sub)
      .maybeSingle();
    if (roleError || assignedRole?.role !== role) return null;
    return {
      email: typeof data.claims.email === "string" ? data.claims.email : null,
      role,
      userId: data.claims.sub,
    };
  },
);
