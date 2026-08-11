"use client";

import { createClient } from "@/lib/supabase/client";
import { type FormEvent, useMemo, useState } from "react";

type Mode = "create" | "signin";

function normalizeEmail(input: string) {
  const email = input.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : null;
}

function friendlyError(message: string) {
  const normalized = message.toLowerCase();
  if (normalized.includes("anonymous sign-ins are disabled")) {
    return "Guest account upgrades are not enabled yet. Please contact support.";
  }
  if (normalized.includes("provider is not enabled")) {
    return "Email sign-in is not enabled yet.";
  }
  if (normalized.includes("rate limit")) {
    return "Too many attempts. Please wait before requesting another link.";
  }
  if (
    normalized.includes("already been registered") ||
    normalized.includes("already registered")
  ) {
    return "This email already has an account. Choose Sign in instead.";
  }
  return message;
}

export default function AuthForm() {
  const supabase = useMemo(() => createClient(), []);
  const [mode, setMode] = useState<Mode>("create");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function requestEmailLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextEmail = normalizeEmail(email);
    if (!nextEmail) {
      setMessage("Enter a valid email address.");
      return;
    }

    setBusy(true);
    setMessage(null);
    const emailRedirectTo = `${window.location.origin}/auth/callback?next=/account`;

    try {
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithOtp({
          email: nextEmail,
          options: { emailRedirectTo, shouldCreateUser: false },
        });
        if (error) throw error;
      } else {
        let { data } = await supabase.auth.getUser();
        if (!data.user) {
          const anonymous = await supabase.auth.signInAnonymously();
          if (anonymous.error) throw anonymous.error;
          data = { user: anonymous.data.user };
        }
        if (!data.user?.is_anonymous) {
          window.location.assign("/account");
          return;
        }
        const { error } = await supabase.auth.updateUser(
          { email: nextEmail },
          { emailRedirectTo },
        );
        if (error) throw error;
      }

      setMessage(
        `Check ${nextEmail} for your secure ${mode === "create" ? "account confirmation" : "sign-in"} link.`,
      );
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to send email.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-form">
      <div className="auth-tabs" aria-label="Account action">
        {(["create", "signin"] as const).map((value) => (
          <button
            aria-pressed={mode === value}
            disabled={busy}
            key={value}
            onClick={() => {
              setMode(value);
              setMessage(null);
            }}
            type="button"
          >
            {value === "create" ? "Create account" : "Sign in"}
          </button>
        ))}
      </div>

      <form onSubmit={requestEmailLink}>
        <label htmlFor="email">Email address</label>
        <div className="auth-input-field">
          <input
            autoCapitalize="none"
            autoComplete="email"
            id="email"
            inputMode="email"
            maxLength={254}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
            spellCheck={false}
            type="email"
            value={email}
          />
        </div>
        <p className="auth-input-hint">
          We&apos;ll email you a secure link. No password required.
        </p>
        <button
          className="pill pill-dark auth-submit"
          disabled={busy}
          type="submit"
        >
          {busy
            ? "Sending link…"
            : mode === "create"
              ? "Continue with email"
              : "Send sign-in link"}
        </button>
      </form>

      {message ? (
        <p className="auth-message" role="status">
          {message}
        </p>
      ) : null}
      <p className="auth-privacy">
        No password, PINFL, or passport number required.
      </p>
    </div>
  );
}
