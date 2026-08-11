import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import AccountSettings from "./account-settings";

export const metadata = { title: "Your account | Uzbekistan OS" };

export default async function AccountPage() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user || data.user.is_anonymous) redirect("/signup");

  const { data: profile } = await supabase
    .from("profiles")
    .select(
      "first_name, last_name, display_name, nationality, avatar_path, identity_level",
    )
    .eq("user_id", data.user.id)
    .maybeSingle();

  const avatarPath = profile?.avatar_path ?? null;
  const avatarUrl = avatarPath
    ? ((
        await supabase.storage.from("avatars").createSignedUrl(avatarPath, 3600)
      ).data?.signedUrl ?? null)
    : null;
  const profileName = [profile?.first_name, profile?.last_name]
    .filter(Boolean)
    .join(" ");

  return (
    <main className="account-page">
      <Link className="signup-brand" href="/">
        Uzbekistan OS
      </Link>
      <section className="account-card">
        <p className="section-kicker">Your account</p>
        <div className="account-hero">
          <div>
            <h1>
              {profileName ||
                profile?.display_name ||
                "Welcome to Uzbekistan OS"}
            </h1>
            <p>
              Keep your personal details and verified sign-in methods up to
              date.
            </p>
          </div>
          <span className="account-verification">
            {profile?.identity_level === 2 ? "Verified account" : "Account"}
          </span>
        </div>

        <AccountSettings
          initialEmail={data.user.email ?? ""}
          initialPhone={data.user.phone ?? ""}
          initialProfile={{
            firstName: profile?.first_name ?? "",
            lastName: profile?.last_name ?? "",
            nationality: profile?.nationality ?? "",
            avatarPath,
            avatarUrl,
          }}
          userId={data.user.id}
        />

        <footer className="account-actions">
          <Link className="pill pill-dark" href="/chat">
            Open assistant
          </Link>
          <form action="/auth/signout" method="post">
            <button className="pill pill-light" type="submit">
              Sign out
            </button>
          </form>
        </footer>
      </section>
    </main>
  );
}
