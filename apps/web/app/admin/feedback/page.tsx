import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getStaffIdentity } from "@/lib/admin-auth";
import {
  listFeedbackForStaff,
  parseFeedbackFilters,
} from "@/lib/admin-feedback";
import FeedbackDashboard from "./feedback-dashboard";

export const metadata: Metadata = {
  title: "Feedback review | Uzbekistan OS",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

type FeedbackPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AdminFeedbackPage({
  searchParams,
}: FeedbackPageProps) {
  const identity = await getStaffIdentity();
  if (!identity) redirect("/account");

  const filters = parseFeedbackFilters(await searchParams);
  const data = await listFeedbackForStaff(identity, filters);

  return (
    <FeedbackDashboard data={data} filters={filters} identity={identity} />
  );
}
