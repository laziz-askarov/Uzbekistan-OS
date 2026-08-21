import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getStaffIdentity } from "@/lib/admin-auth";
import OperationsDashboard from "./operations-dashboard";

export const metadata: Metadata = {
  title: "System analytics and operations · Uzbekistan OS",
  description:
    "Internal service health, error, source, upload, and crawler operations for Uzbekistan OS.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function AdminOperationsPage() {
  const identity = await getStaffIdentity();
  if (identity?.role !== "admin") redirect("/account");

  return <OperationsDashboard />;
}
