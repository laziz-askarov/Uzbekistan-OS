"use client";

import { createClient } from "@/lib/supabase/client";
import { normalizeEmail, normalizeInternationalPhone } from "@/lib/auth-inputs";
import { TurnstileWidget } from "@/components/turnstile-widget";
import Link from "next/link";
import { type FormEvent, useCallback, useMemo, useState } from "react";

type Mode = "create" | "signin";
type Method = "email" | "phone";

function friendlyError(message: string, method: Method) {
  const normalized = message.toLowerCase();
  if (normalized.includes("provider is not enabled")) {
    return `${method === "email" ? "Email" : "Phone"} sign-in is not enabled yet.`;
  }
  if (normalized.includes("rate limit")) {
    return "Too many attempts. Please wait before trying again.";
  }
  if (normalized.includes("captcha")) {
    return "Complete the security check and try again.";
  }
  if (normalized.includes("password should be")) {
    return "Use a password with at least 8 characters.";
  }
  if (normalized.includes("invalid login credentials")) {
    return `${method === "email" ? "Email" : "Phone number"} or password is incorrect.`;
  }
  if (normalized.includes("email not confirmed")) {
    return "Confirm your email before signing in.";
  }
  if (
    normalized.includes("already been registered") ||
    normalized.includes("already registered")
  ) {
    return `This ${method === "email" ? "email" : "number"} already has an account. Sign in instead.`;
  }
  return message;
}

export default function AuthForm() {
  const supabase = useMemo(() => createClient(), []);
  const turnstileSiteKey =
    process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim() ?? "";
  const captchaEnabled = turnstileSiteKey.length > 0;
  const [mode, setMode] = useState<Mode>("create");
  const [method, setMethod] = useState<Method>("email");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [phoneStep, setPhoneStep] = useState<"credentials" | "otp">(
    "credentials",
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaResetSignal, setCaptchaResetSignal] = useState(0);

  const handleCaptchaError = useCallback(() => {
    setMessage(
      "The security check could not load. Please refresh and try again.",
    );
  }, []);

  function resetCaptcha() {
    setCaptchaToken(null);
    setCaptchaResetSignal((current) => current + 1);
  }

  function hasCaptchaToken() {
    if (captchaEnabled && !captchaToken) {
      setMessage("Complete the security check before continuing.");
      return false;
    }
    return true;
  }

  function resetFeedback() {
    setPhoneStep("credentials");
    setOtp("");
    setPassword("");
    setMessage(null);
    resetCaptcha();
  }

  function switchMode() {
    setMode((current) => (current === "create" ? "signin" : "create"));
    resetFeedback();
  }

  function validatePassword() {
    if (password.length < 8) {
      setMessage("Use a password with at least 8 characters.");
      return false;
    }
    return true;
  }

  async function submitEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextEmail = normalizeEmail(email);
    if (!nextEmail) {
      setMessage("Enter a valid email address.");
      return;
    }
    if (!validatePassword()) return;
    if (!hasCaptchaToken()) return;

    setBusy(true);
    setMessage(null);
    try {
      if (mode === "create") {
        const { data, error } = await supabase.auth.signUp({
          email: nextEmail,
          password,
          options: {
            ...(captchaToken ? { captchaToken } : {}),
            emailRedirectTo: `${window.location.origin}/auth/callback?next=/account`,
          },
        });
        if (error) throw error;
        if (data.session) {
          window.location.assign("/account");
          return;
        }
        setMessage(`Check ${nextEmail} to confirm your account.`);
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: nextEmail,
          password,
          options: captchaToken ? { captchaToken } : undefined,
        });
        if (error) throw error;
        window.location.assign("/account");
      }
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to continue.",
          "email",
        ),
      );
    } finally {
      setBusy(false);
      resetCaptcha();
    }
  }

  async function sendPasswordRecovery() {
    const nextEmail = normalizeEmail(email);
    if (!nextEmail) {
      setMessage("Enter your account email address first.");
      return;
    }
    if (!hasCaptchaToken()) return;

    setBusy(true);
    setMessage(null);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(nextEmail, {
        ...(captchaToken ? { captchaToken } : {}),
        redirectTo: `${window.location.origin}/auth/callback?next=/account/password`,
      });
      if (error) throw error;
      setMessage(`We sent password recovery instructions to ${nextEmail}.`);
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error
            ? error.message
            : "Unable to send recovery instructions.",
          "email",
        ),
      );
    } finally {
      setBusy(false);
      resetCaptcha();
    }
  }

  async function submitPhone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPhone = normalizeInternationalPhone(phone);
    if (!nextPhone) {
      setMessage(
        "Enter a valid international mobile number with its country code, such as +998 90 123 45 67.",
      );
      return;
    }
    if (!validatePassword()) return;
    if (!hasCaptchaToken()) return;

    setBusy(true);
    setMessage(null);
    try {
      if (mode === "create") {
        const { data, error } = await supabase.auth.signUp({
          phone: nextPhone,
          password,
          options: {
            ...(captchaToken ? { captchaToken } : {}),
            channel: "sms",
          },
        });
        if (error) throw error;
        if (data.session) {
          window.location.assign("/account");
          return;
        }
        setNormalizedPhone(nextPhone);
        setPhoneStep("otp");
        setMessage(`We sent a 6-digit verification code to ${nextPhone}.`);
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          phone: nextPhone,
          password,
          options: captchaToken ? { captchaToken } : undefined,
        });
        if (error) throw error;
        window.location.assign("/account");
      }
    } catch (error) {
      setMessage(
        friendlyError(
          error instanceof Error ? error.message : "Unable to continue.",
          "phone",
        ),
      );
    } finally {
      setBusy(false);
      resetCaptcha();
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

  const submitLabel = mode === "create" ? "Create account" : "Sign in";

  return (
    <div className="auth-form">
      <div className="auth-methods" aria-label="Account method">
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
        <form onSubmit={submitEmail}>
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
          <label htmlFor="email-password">Password</label>
          <div className="auth-input-field">
            <input
              autoComplete={
                mode === "create" ? "new-password" : "current-password"
              }
              id="email-password"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
              type="password"
              value={password}
            />
          </div>
          <p className="auth-input-hint">
            {mode === "create"
              ? "We'll email you a confirmation link after signup."
              : "Use the email and password for your account."}
          </p>
          {captchaEnabled ? (
            <TurnstileWidget
              onError={handleCaptchaError}
              onToken={setCaptchaToken}
              resetSignal={captchaResetSignal}
              siteKey={turnstileSiteKey}
            />
          ) : null}
          <button
            className="pill pill-dark auth-submit"
            disabled={busy || (captchaEnabled && !captchaToken)}
            type="submit"
          >
            {busy ? "Please wait…" : submitLabel}
          </button>
          <button
            className="auth-mode-switch"
            disabled={busy}
            onClick={switchMode}
            type="button"
          >
            {mode === "create"
              ? "Already have an account? Sign in"
              : "Need an account? Create one"}
          </button>
          {mode === "signin" ? (
            <button
              className="auth-recovery"
              disabled={busy}
              onClick={sendPasswordRecovery}
              type="button"
            >
              Forgot password? Recover by email
            </button>
          ) : null}
        </form>
      ) : phoneStep === "credentials" ? (
        <form onSubmit={submitPhone}>
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
          <label htmlFor="phone-password">Password</label>
          <div className="auth-input-field">
            <input
              autoComplete={
                mode === "create" ? "new-password" : "current-password"
              }
              id="phone-password"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
              type="password"
              value={password}
            />
          </div>
          <p className="phone-hint">
            {mode === "create"
              ? "We'll text you a verification code after signup."
              : "Use your international phone number and password."}
          </p>
          {captchaEnabled ? (
            <TurnstileWidget
              onError={handleCaptchaError}
              onToken={setCaptchaToken}
              resetSignal={captchaResetSignal}
              siteKey={turnstileSiteKey}
            />
          ) : null}
          <button
            className="pill pill-dark auth-submit"
            disabled={busy || (captchaEnabled && !captchaToken)}
            type="submit"
          >
            {busy ? "Please wait…" : submitLabel}
          </button>
          <button
            className="auth-mode-switch"
            disabled={busy}
            onClick={switchMode}
            type="button"
          >
            {mode === "create"
              ? "Already have an account? Sign in"
              : "Need an account? Create one"}
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
            onClick={() => setPhoneStep("credentials")}
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
        By creating an account, you agree to the{" "}
        <Link href="/terms">Terms of Use</Link> and acknowledge the{" "}
        <Link href="/privacy">Privacy Policy</Link>.
        {" No PINFL or passport number required."}
      </p>
    </div>
  );
}
