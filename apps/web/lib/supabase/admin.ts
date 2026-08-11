import { createClient } from "@supabase/supabase-js";

function requiredServerVariable(...names: string[]) {
  for (const name of names) {
    const value = process.env[name]?.trim();
    if (value) return value;
  }
  throw new Error(
    `Missing required server configuration: ${names.join(" or ")}`,
  );
}

export function createAdminClient() {
  const url = requiredServerVariable(
    "SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
  );
  const secretKey = requiredServerVariable(
    "SUPABASE_SECRET_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
  );

  return createClient(url, secretKey, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false,
    },
  });
}
