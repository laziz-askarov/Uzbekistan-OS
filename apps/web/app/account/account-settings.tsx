"use client";

import { normalizeEmail, normalizeInternationalPhone } from "@/lib/auth-inputs";
import { createClient } from "@/lib/supabase/client";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { type ChangeEvent, type FormEvent, useMemo, useState } from "react";

type AccountSettingsProps = {
  userId: string;
  initialEmail: string;
  initialPhone: string;
  initialProfile: {
    firstName: string;
    lastName: string;
    nationality: string;
    avatarPath: string | null;
    avatarUrl: string | null;
  };
};

type Notice = { kind: "success" | "error"; text: string } | null;

const avatarTypes = new Set(["image/jpeg", "image/png", "image/webp"]);

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function AccountSettings({
  userId,
  initialEmail,
  initialPhone,
  initialProfile,
}: AccountSettingsProps) {
  const router = useRouter();
  const supabase = useMemo(() => createClient(), []);
  const [firstName, setFirstName] = useState(initialProfile.firstName);
  const [lastName, setLastName] = useState(initialProfile.lastName);
  const [nationality, setNationality] = useState(initialProfile.nationality);
  const [avatarPath, setAvatarPath] = useState(initialProfile.avatarPath);
  const [avatarUrl, setAvatarUrl] = useState(initialProfile.avatarUrl);
  const [currentEmail] = useState(initialEmail);
  const [email, setEmail] = useState(initialEmail);
  const [currentPhone, setCurrentPhone] = useState(initialPhone);
  const [phone, setPhone] = useState(initialPhone);
  const [pendingPhone, setPendingPhone] = useState<string | null>(null);
  const [phoneOtp, setPhoneOtp] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const initials =
    `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || "U";

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanFirstName = firstName.trim();
    const cleanLastName = lastName.trim();
    const cleanNationality = nationality.trim();
    if (!cleanFirstName || !cleanLastName) {
      setNotice({ kind: "error", text: "Enter your first and last name." });
      return;
    }

    setBusy("profile");
    setNotice(null);
    try {
      const { error } = await supabase
        .from("profiles")
        .update({
          first_name: cleanFirstName,
          last_name: cleanLastName,
          display_name: `${cleanFirstName} ${cleanLastName}`,
          nationality: cleanNationality || null,
        })
        .eq("user_id", userId);
      if (error) throw error;
      setFirstName(cleanFirstName);
      setLastName(cleanLastName);
      setNationality(cleanNationality);
      setNotice({ kind: "success", text: "Profile details saved." });
      router.refresh();
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to save your profile."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function uploadAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!avatarTypes.has(file.type)) {
      setNotice({
        kind: "error",
        text: "Choose a JPG, PNG, or WebP profile image.",
      });
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setNotice({ kind: "error", text: "Profile images must be under 2 MB." });
      return;
    }

    setBusy("avatar");
    setNotice(null);
    try {
      const path = `${userId}/avatar`;
      const { error: uploadError } = await supabase.storage
        .from("avatars")
        .upload(path, file, {
          cacheControl: "3600",
          contentType: file.type,
          upsert: true,
        });
      if (uploadError) throw uploadError;

      const { error: profileError } = await supabase
        .from("profiles")
        .update({ avatar_path: path })
        .eq("user_id", userId);
      if (profileError) throw profileError;

      const { data, error: signedUrlError } = await supabase.storage
        .from("avatars")
        .createSignedUrl(path, 3600);
      if (signedUrlError) throw signedUrlError;
      setAvatarPath(path);
      setAvatarUrl(data.signedUrl);
      setNotice({ kind: "success", text: "Profile image updated." });
      router.refresh();
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to update your profile image."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function removeAvatar() {
    if (!avatarPath) return;
    setBusy("avatar");
    setNotice(null);
    try {
      const { error: removeError } = await supabase.storage
        .from("avatars")
        .remove([avatarPath]);
      if (removeError) throw removeError;
      const { error: profileError } = await supabase
        .from("profiles")
        .update({ avatar_path: null })
        .eq("user_id", userId);
      if (profileError) throw profileError;
      setAvatarPath(null);
      setAvatarUrl(null);
      setNotice({ kind: "success", text: "Profile image removed." });
      router.refresh();
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to remove your profile image."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function updateEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextEmail = normalizeEmail(email);
    if (!nextEmail) {
      setNotice({ kind: "error", text: "Enter a valid email address." });
      return;
    }
    if (nextEmail === currentEmail) {
      setNotice({ kind: "success", text: "Your email is already up to date." });
      return;
    }

    setBusy("email");
    setNotice(null);
    try {
      const { error } = await supabase.auth.updateUser(
        { email: nextEmail },
        {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=/account`,
        },
      );
      if (error) throw error;
      setNotice({
        kind: "success",
        text: `Check ${nextEmail} to confirm the email change.`,
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to update your email."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function updatePhone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPhone = normalizeInternationalPhone(phone);
    if (!nextPhone) {
      setNotice({
        kind: "error",
        text: "Enter a valid international number with its country code.",
      });
      return;
    }
    if (nextPhone === currentPhone) {
      setNotice({
        kind: "success",
        text: "Your phone number is already up to date.",
      });
      return;
    }

    setBusy("phone");
    setNotice(null);
    try {
      const { error } = await supabase.auth.updateUser({ phone: nextPhone });
      if (error) throw error;
      setPendingPhone(nextPhone);
      setPhoneOtp("");
      setNotice({
        kind: "success",
        text: `We sent a verification code to ${nextPhone}.`,
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to update your phone number."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function verifyPhoneChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pendingPhone || !/^\d{6}$/.test(phoneOtp)) {
      setNotice({ kind: "error", text: "Enter the 6-digit SMS code." });
      return;
    }

    setBusy("phone-otp");
    setNotice(null);
    try {
      const { error } = await supabase.auth.verifyOtp({
        phone: pendingPhone,
        token: phoneOtp,
        type: "phone_change",
      });
      if (error) throw error;
      setCurrentPhone(pendingPhone);
      setPhone(pendingPhone);
      setPendingPhone(null);
      setPhoneOtp("");
      setNotice({ kind: "success", text: "Phone number verified and saved." });
      router.refresh();
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to verify the phone number."),
      });
    } finally {
      setBusy(null);
    }
  }

  async function sendPasswordRecovery() {
    if (!currentEmail) {
      setNotice({
        kind: "error",
        text: "Add and verify an email address before using password recovery.",
      });
      return;
    }

    setBusy("recovery");
    setNotice(null);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(
        currentEmail,
        {
          redirectTo: `${window.location.origin}/auth/callback?next=/account/password`,
        },
      );
      if (error) throw error;
      setNotice({
        kind: "success",
        text: `Password recovery instructions were sent to ${currentEmail}.`,
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: errorMessage(error, "Unable to send password recovery email."),
      });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="account-settings">
      <section className="account-section" aria-labelledby="profile-heading">
        <div className="account-section-heading">
          <div>
            <p className="section-kicker">Profile</p>
            <h2 id="profile-heading">Personal details</h2>
          </div>
          <div className="profile-image-control">
            <div className="profile-avatar" aria-label="Current profile image">
              {avatarUrl ? (
                <Image
                  alt="Your profile"
                  fill
                  sizes="88px"
                  src={avatarUrl}
                  unoptimized
                />
              ) : (
                <span aria-hidden="true">{initials}</span>
              )}
            </div>
            <div className="profile-image-actions">
              <label className="pill pill-light" htmlFor="profile-image">
                {busy === "avatar" ? "Uploading…" : "Choose image"}
              </label>
              <input
                accept="image/jpeg,image/png,image/webp"
                disabled={busy !== null}
                id="profile-image"
                onChange={uploadAvatar}
                type="file"
              />
              {avatarPath ? (
                <button
                  className="account-text-action"
                  disabled={busy !== null}
                  onClick={removeAvatar}
                  type="button"
                >
                  Remove
                </button>
              ) : null}
            </div>
          </div>
        </div>

        <form className="account-form" onSubmit={saveProfile}>
          <div className="account-form-grid">
            <label>
              <span>First name</span>
              <input
                autoComplete="given-name"
                maxLength={80}
                onChange={(event) => setFirstName(event.target.value)}
                required
                value={firstName}
              />
            </label>
            <label>
              <span>Last name</span>
              <input
                autoComplete="family-name"
                maxLength={80}
                onChange={(event) => setLastName(event.target.value)}
                required
                value={lastName}
              />
            </label>
          </div>
          <label>
            <span>Nationality</span>
            <input
              autoComplete="country-name"
              maxLength={100}
              onChange={(event) => setNationality(event.target.value)}
              placeholder="Country shown on your passport"
              value={nationality}
            />
          </label>
          <button
            className="pill pill-dark account-save"
            disabled={busy !== null}
            type="submit"
          >
            {busy === "profile" ? "Saving…" : "Save profile"}
          </button>
        </form>
      </section>

      <section className="account-section" aria-labelledby="contact-heading">
        <p className="section-kicker">Sign-in & recovery</p>
        <h2 id="contact-heading">Contact details</h2>
        <p className="account-section-copy">
          Changes to verified contact details require confirmation.
        </p>

        <form className="account-inline-form" onSubmit={updateEmail}>
          <label htmlFor="account-email">Email</label>
          <div>
            <input
              autoCapitalize="none"
              autoComplete="email"
              id="account-email"
              inputMode="email"
              maxLength={254}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              spellCheck={false}
              type="email"
              value={email}
            />
            <button
              className="pill pill-light"
              disabled={busy !== null}
              type="submit"
            >
              {busy === "email"
                ? "Sending…"
                : currentEmail
                  ? "Update email"
                  : "Add email"}
            </button>
          </div>
          <small>
            {currentEmail
              ? `Verified account email: ${currentEmail}`
              : "Add an email to enable password recovery."}
          </small>
        </form>

        <form className="account-inline-form" onSubmit={updatePhone}>
          <label htmlFor="account-phone">Phone</label>
          <div>
            <input
              autoComplete="tel"
              id="account-phone"
              inputMode="tel"
              maxLength={24}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+998 90 123 45 67"
              type="tel"
              value={phone}
            />
            <button
              className="pill pill-light"
              disabled={busy !== null}
              type="submit"
            >
              {busy === "phone"
                ? "Sending…"
                : currentPhone
                  ? "Update phone"
                  : "Add phone"}
            </button>
          </div>
          <small>
            {currentPhone
              ? `Verified account number: ${currentPhone}`
              : "Use an international number with its country code."}
          </small>
        </form>

        {pendingPhone ? (
          <form className="account-inline-form" onSubmit={verifyPhoneChange}>
            <label htmlFor="account-phone-otp">SMS verification code</label>
            <div>
              <input
                autoComplete="one-time-code"
                id="account-phone-otp"
                inputMode="numeric"
                maxLength={6}
                onChange={(event) =>
                  setPhoneOtp(event.target.value.replace(/\D/g, ""))
                }
                placeholder="000000"
                required
                value={phoneOtp}
              />
              <button
                className="pill pill-dark"
                disabled={busy !== null}
                type="submit"
              >
                {busy === "phone-otp" ? "Verifying…" : "Verify phone"}
              </button>
            </div>
          </form>
        ) : null}

        <div className="account-recovery">
          <div>
            <strong>Password recovery</strong>
            <span>
              Receive a secure password-reset link at your verified email.
            </span>
          </div>
          <button
            className="pill pill-light"
            disabled={busy !== null || !currentEmail}
            onClick={sendPasswordRecovery}
            type="button"
          >
            {busy === "recovery" ? "Sending…" : "Send recovery email"}
          </button>
        </div>
      </section>

      {notice ? (
        <p
          className={`account-notice account-notice-${notice.kind}`}
          role="status"
        >
          {notice.text}
        </p>
      ) : null}
    </div>
  );
}
