import "server-only";
import { createClient } from "@/lib/supabase/server";

export async function getBlogIdentity() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getSession();
  if (!data.session) return null;
  const base = (
    process.env.GROUNDED_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");
  const response = await fetch(`${base}/auth/me`, {
    headers: { authorization: `Bearer ${data.session.access_token}` },
    cache: "no-store",
  });
  if (!response.ok) return null;
  const payload = (await response.json()) as {
    data: { id: string; roles: string[] };
  };
  return payload.data;
}
