import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Your account | Uzbekistan OS" };

export default async function AccountPage() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user || data.user.is_anonymous) redirect("/signup");

  const { data: profile } = await supabase
    .from("profiles")
    .select("display_name, preferred_language, identity_level")
    .eq("user_id", data.user.id)
    .maybeSingle();
  const contact = data.user.email ?? data.user.phone ?? "Verified account";
  const contactLabel = data.user.email ? "Email" : "Phone";

  return (
    <main className="account-page">
      <Link className="signup-brand" href="/">
        Uzbekistan OS
      </Link>
      <section className="account-card">
        <p className="section-kicker">Your account</p>
        <h1>{profile?.display_name || "Welcome to Uzbekistan OS"}</h1>
        <p>Your conversations and saved plans are protected by your account.</p>
        <dl>
          <div>
            <dt>{contactLabel}</dt>
            <dd>{contact}</dd>
          </div>
          <div>
            <dt>Identity level</dt>
            <dd>
              {profile?.identity_level === 2
                ? `${contactLabel} verified`
                : "Account"}
            </dd>
          </div>
          <div>
            <dt>Language</dt>
            <dd>{profile?.preferred_language ?? "English"}</dd>
          </div>
        </dl>
        <div className="account-actions">
          <Link className="pill pill-dark" href="/chat">
            Open assistant
          </Link>
          <form action="/auth/signout" method="post">
            <button className="pill pill-light" type="submit">
              Sign out
            </button>
          </form>
        </div>
        <p className="account-note">
          OneID verification will only be requested for future
          identity-dependent government services.
        </p>
      </section>
    </main>
  );
}
