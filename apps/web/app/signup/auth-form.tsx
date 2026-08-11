"use client";

import { createClient } from "@/lib/supabase/client";
import { type FormEvent, useMemo, useState } from "react";

type Mode = "create" | "signin";
type Method = "email" | "phone";

function normalizeEmail(input: string) {
  const email = input.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : null;
}

function normalizeInternationalPhone(input: string) {
  const compact = input.trim().replace(/[\s().-]/g, "");
  const candidate = compact.startsWith("+")
    ? compact
    : /^998\d{9}$/.test(compact)
      ? `+${compact}`
      : /^\d{9}$/.test(compact)
        ? `+998${compact}`
        : null;
  return candidate && /^\+[1-9]\d{7,14}$/.test(candidate) ? candidate : null;
}

function friendlyError(message: string, method: Method) {
  const normalized = message.toLowerCase();
  if (normalized.includes("provider is not enabled")) {
    return `${method === "email" ? "Email" : "Phone"} sign-in is not enabled yet.`;
  }
  if (normalized.includes("rate limit")) {
    return `Too many attempts. Please wait before requesting another ${method === "email" ? "link" : "code"}.`;
  }
  if (
    normalized.includes("already been registered") ||
    normalized.includes("already registered")
  ) {
    return `This ${method === "email" ? "email" : "number"} already has an account. Choose Sign in instead.`;
  }
  return message;
}

export default function AuthForm() {
  const supabase = useMemo(() => createClient(), []);
  const [mode, setMode] = useState<Mode>("create");
  const [method, setMethod] = useState<Method>("email");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [phoneStep, setPhoneStep] = useState<"phone" | "otp">("phone");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function resetFeedback() {
    setPhoneStep("phone");
    setOtp("");
    setMessage(null);
  }

  async function requestEmailLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextEmail = normalizeEmail(email);
    if (!nextEmail) {
      setMessage("Enter a valid email address.");
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email: nextEmail,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=/account`,
          shouldCreateUser: mode === "create",
        },
      });
      if (error) throw error;
      setMessage(
        `Check ${nextEmail} for your secure ${mode === "create" ? "account confirmation" : "sign-in"} link.`,
      );
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to send email.",
          "email",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function requestPhoneOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPhone = normalizeInternationalPhone(phone);
    if (!nextPhone) {
      setMessage(
        "Enter a valid international mobile number with its country code, such as +998 90 123 45 67.",
      );
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const { error } = await supabase.auth.signInWithOtp({
        phone: nextPhone,
        options: { shouldCreateUser: mode === "create" },
      });
      if (error) throw error;
      setNormalizedPhone(nextPhone);
      setPhoneStep("otp");
      setMessage(`We sent a 6-digit code to ${nextPhone}.`);
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to send code.",
          "phone",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function verifyPhoneOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!normalizedPhone || !/^\d{6}$/.test(otp)) {
      setMessage("Enter the 6-digit code from your text message.");
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const { error } = await supabase.auth.verifyOtp({
        phone: normalizedPhone,
        token: otp,
        type: "sms",
      });
      if (error) throw error;
      window.location.assign("/account");
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to verify code.",
          "phone",
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
              resetFeedback();
            }}
            type="button"
          >
            {value === "create" ? "Create account" : "Sign in"}
          </button>
        ))}
      </div>

      <div className="auth-methods" aria-label="Sign-up method">
        {(["email", "phone"] as const).map((value) => (
          <button
            aria-pressed={method === value}
            disabled={busy}
            key={value}
            onClick={() => {
              setMethod(value);
              resetFeedback();
            }}
            type="button"
          >
            {value === "email" ? "Email" : "Phone"}
          </button>
        ))}
      </div>

      {method === "email" ? (
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
      ) : phoneStep === "phone" ? (
        <form onSubmit={requestPhoneOtp}>
          <label htmlFor="phone">Mobile number</label>
          <div className="phone-field">
            <input
              autoComplete="tel"
              id="phone"
              inputMode="tel"
              maxLength={24}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+998 90 123 45 67"
              required
              type="tel"
              value={phone}
            />
          </div>
          <p className="phone-hint">
            Uzbekistan numbers can be entered with or without +998. Other
            countries require the international country code.
          </p>
          <button
            className="pill pill-dark auth-submit"
            disabled={busy}
            type="submit"
          >
            {busy
              ? "Sending code…"
              : mode === "create"
                ? "Continue with phone"
                : "Send sign-in code"}
          </button>
        </form>
      ) : (
        <form onSubmit={verifyPhoneOtp}>
          <label htmlFor="otp">Verification code</label>
          <input
            autoComplete="one-time-code"
            className="otp-field"
            id="otp"
            inputMode="numeric"
            maxLength={6}
            onChange={(event) => setOtp(event.target.value.replace(/\D/g, ""))}
            placeholder="000000"
            required
            value={otp}
          />
          <button
            className="pill pill-dark auth-submit"
            disabled={busy}
            type="submit"
          >
            {busy ? "Verifying…" : "Verify and continue"}
          </button>
          <button
            className="auth-back"
            disabled={busy}
            onClick={() => setPhoneStep("phone")}
            type="button"
          >
            Use a different number
          </button>
        </form>
      )}

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
