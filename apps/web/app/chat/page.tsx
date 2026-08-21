import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getStaffIdentity } from "@/lib/admin-auth";
import { createClient } from "@/lib/supabase/server";
import ChatWorkspace from "./chat-workspace";

export const metadata: Metadata = {
  title: "Visa Assistant | Uzbekistan OS",
  description:
    "A signed-in workspace preview for structured, official-source-backed Uzbekistan visa guidance.",
};

export default async function ChatPage() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user || data.user.is_anonymous) redirect("/signup");
  const staffIdentity = await getStaffIdentity();

  return <ChatWorkspace staffRole={staffIdentity?.role ?? null} />;
}
