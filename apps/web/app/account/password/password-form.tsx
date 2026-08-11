"use client";

import { createClient } from "@/lib/supabase/client";
import { type FormEvent, useMemo, useState } from "react";

export default function PasswordForm() {
  const supabase = useMemo(() => createClient(), []);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 8) {
      setMessage("Use a password with at least 8 characters.");
      return;
    }
    if (password !== confirmation) {
      setMessage("The passwords do not match.");
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      window.location.assign("/account");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to update password.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="account-form password-form" onSubmit={updatePassword}>
      <label>
        <span>New password</span>
        <input
          autoComplete="new-password"
          minLength={8}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <label>
        <span>Confirm new password</span>
        <input
          autoComplete="new-password"
          minLength={8}
          onChange={(event) => setConfirmation(event.target.value)}
          required
          type="password"
          value={confirmation}
        />
      </label>
      <button
        className="pill pill-dark account-save"
        disabled={busy}
        type="submit"
      >
        {busy ? "Updating…" : "Update password"}
      </button>
      {message ? (
        <p className="account-notice account-notice-error" role="status">
          {message}
        </p>
      ) : null}
    </form>
  );
}
