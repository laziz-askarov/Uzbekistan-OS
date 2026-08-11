"use client";

import { createClient } from "@/lib/supabase/client";
import { type FormEvent, useMemo, useState } from "react";

type Mode = "create" | "signin";

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

function friendlyError(message: string) {
  const normalized = message.toLowerCase();
  if (normalized.includes("anonymous sign-ins are disabled")) {
    return "Guest account upgrades are not enabled yet. Please contact support.";
  }
  if (normalized.includes("provider is not enabled")) {
    return "This sign-in option is not enabled yet.";
  }
  if (normalized.includes("rate limit")) {
    return "Too many attempts. Please wait before requesting another code.";
  }
  if (normalized.includes("already been registered")) {
    return "This number already has an account. Choose Sign in instead.";
  }
  return message;
}

export default function AuthForm() {
  const supabase = useMemo(() => createClient(), []);
  const [mode, setMode] = useState<Mode>("create");
  const [phone, setPhone] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function requestOtp(event: FormEvent<HTMLFormElement>) {
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
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithOtp({
          phone: nextPhone,
          options: { shouldCreateUser: false },
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
        const { error } = await supabase.auth.updateUser({ phone: nextPhone });
        if (error) throw error;
      }
      setNormalizedPhone(nextPhone);
      setStep("otp");
      setMessage(`We sent a 6-digit code to ${nextPhone}.`);
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to send code.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(event: FormEvent<HTMLFormElement>) {
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
        type: mode === "create" ? "phone_change" : "sms",
      });
      if (error) throw error;
      window.location.assign("/account");
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to verify code.",
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
              setStep("phone");
              setMessage(null);
            }}
            type="button"
          >
            {value === "create" ? "Create account" : "Sign in"}
          </button>
        ))}
      </div>

      {step === "phone" ? (
        <form onSubmit={requestOtp}>
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
        <form onSubmit={verifyOtp}>
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
            onClick={() => setStep("phone")}
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
