import "server-only";

import { createAdminClient } from "@/lib/supabase/admin";

export type TripInquiryRecord = {
  id: string;
  created_at: string;
  status: "new" | "replied" | "closed" | "spam";
  name: string;
  email: string;
  travel_month: string;
  nights: number;
  travellers: number;
  interests: string[];
  comfort: string;
  budget: string;
  message: string;
  source_path: string | null;
};

export async function listTripInquiries(
  limit = 100,
): Promise<TripInquiryRecord[]> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("trip_inquiries")
    .select(
      "id, created_at, status, name, email, travel_month, nights, travellers, interests, comfort, budget, message, source_path",
    )
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return (data ?? []) as TripInquiryRecord[];
}
