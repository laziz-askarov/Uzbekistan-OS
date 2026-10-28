import { redirect } from "next/navigation";
import Link from "next/link";
import { getBlogIdentity } from "@/lib/blog-auth";
import BlogPermissions from "./permissions";

export const metadata = {
  title: "Blog permissions · Uzbekistan OS",
  robots: { index: false, follow: false },
};
export default async function BlogPermissionsPage() {
  const identity = await getBlogIdentity();
  if (!identity?.roles.includes("admin")) redirect("/account");
  return (
    <main style={{ maxWidth: 800, margin: "3rem auto", padding: "1.5rem" }}>
      <Link href="/admin/content">Back to blog studio</Link>
      <h1>Blog permissions</h1>
      <p>
        Grant permissions to a registered user by email. Clear all permissions
        to revoke access. Publishing requires an approved revision;
        administrators review submitted drafts.
      </p>
      <BlogPermissions />
    </main>
  );
}
