import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getStaffIdentity } from "@/lib/admin-auth";
import ReviewConsole from "./review-console";

export const metadata: Metadata = {
  title: "Review queue · Uzbekistan OS",
  description: "Internal evidence review operations for Uzbekistan OS.",
};

export const dynamic = "force-dynamic";

export default async function ReviewQueuePage() {
  const identity = await getStaffIdentity();
  if (!identity) redirect("/account");

  return <ReviewConsole />;
}
