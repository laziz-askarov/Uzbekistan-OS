import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import PasswordForm from "./password-form";

export const metadata = { title: "Update password | Uzbekistan OS" };

export default async function PasswordPage() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user || data.user.is_anonymous) redirect("/signup");

  return (
    <main className="account-page account-password-page">
      <Link className="signup-brand" href="/">
        Uzbekistan OS
      </Link>
      <section className="account-card password-card">
        <p className="section-kicker">Account security</p>
        <h1>Choose a new password</h1>
        <p>Use at least eight characters and keep it unique to this account.</p>
        <PasswordForm />
        <Link className="signup-back" href="/account">
          Return to account settings
        </Link>
      </section>
    </main>
  );
}
