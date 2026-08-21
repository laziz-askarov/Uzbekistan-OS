"use client";

import type { Session } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type AdminApiSession = {
  accessToken: string | null;
  error: string | null;
  loading: boolean;
};

const signedOutSession: AdminApiSession = {
  accessToken: null,
  error: "Sign in with an authorized staff account to continue.",
  loading: false,
};

export function useAdminApiSession(): AdminApiSession {
  const [session, setSession] = useState<AdminApiSession>({
    accessToken: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    const supabase = createClient();
    let active = true;

    function applySession(nextSession: Session | null) {
      if (!active) return;
      if (!nextSession?.access_token || nextSession.user.is_anonymous) {
        setSession(signedOutSession);
        return;
      }
      setSession({
        accessToken: nextSession.access_token,
        error: null,
        loading: false,
      });
    }

    void supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) {
        setSession({
          accessToken: null,
          error: "Your staff session could not be verified. Sign in again.",
          loading: false,
        });
        return;
      }
      applySession(data.session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      applySession(nextSession);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  return session;
}
