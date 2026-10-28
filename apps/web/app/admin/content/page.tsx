import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getBlogIdentity } from "@/lib/blog-auth";
import ContentStudio from "./content-studio";

export const metadata: Metadata = {
  title: "Editorial studio · Uzbekistan OS",
  description:
    "Protected editorial workflow for Uzbekistan OS articles and guides.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function AdminContentPage() {
  const identity = await getBlogIdentity();
  if (
    !identity?.roles.some((role) =>
      [
        "admin",
        "content_author",
        "content_reviewer",
        "knowledge_publisher",
        "blog_create",
        "blog_edit",
        "blog_publish",
      ].includes(role),
    )
  )
    redirect("/account");

  return <ContentStudio />;
}
