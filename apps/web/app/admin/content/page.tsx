import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getStaffIdentity } from "@/lib/admin-auth";
import ContentStudio from "./content-studio";

export const metadata: Metadata = {
  title: "Editorial studio · Uzbekistan OS",
  description:
    "Protected editorial workflow for Uzbekistan OS articles and guides.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function AdminContentPage() {
  const identity = await getStaffIdentity();
  if (identity?.role !== "admin") redirect("/account");

  return <ContentStudio />;
}
