"use client";

import { useState, type FormEvent } from "react";
import {
  BUDGET_BANDS,
  COMFORT_LEVELS,
  INTERESTS,
  MESSAGE_MAX_LENGTH,
  type Option,
} from "@/lib/trip-inquiry";
import styles from "./trips.module.css";

type InquiryFormProps = {
  months: readonly Option[];
  sourcePath?: string;
};

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "done" }
  | { kind: "error"; message: string };

export function InquiryForm({ months, sourcePath }: InquiryFormProps) {
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload = {
      name: data.get("name"),
      email: data.get("email"),
      travelMonth: data.get("travelMonth"),
      nights: data.get("nights"),
      travellers: data.get("travellers"),
      interests: data.getAll("interests"),
      comfort: data.get("comfort"),
      budget: data.get("budget"),
      message: data.get("message") ?? "",
      website: data.get("website") ?? "",
      sourcePath,
    };
    setStatus({ kind: "submitting" });
    try {
      const response = await fetch("/api/trips/inquiry", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.status === 201) {
        setStatus({ kind: "done" });
        form.reset();
        return;
      }
      const body = (await response.json().catch(() => null)) as {
        message?: string;
      } | null;
      setStatus({
        kind: "error",
        message:
          body?.message ?? "We could not send your inquiry. Please try again.",
      });
    } catch {
      setStatus({
        kind: "error",
        message: "We could not reach the server. Check your connection and try again.",
      });
    }
  }

  if (status.kind === "done") {
    return (
      <div className={styles.done} role="status">
        <h3>Thanks, we have your inquiry.</h3>
        <p>
          A member of the Kebab Travel team in Tashkent will reply by email
          with questions or a first plan. Nothing is booked and no payment is
          taken until you confirm.
        </p>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate={false}>
      <div className={styles.row}>
        <div className={styles.field}>
          <label htmlFor="inquiry-name">Your name</label>
          <input
            className={styles.input}
            id="inquiry-name"
            name="name"
            autoComplete="name"
            maxLength={120}
            required
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="inquiry-email">Email</label>
          <input
            className={styles.input}
            id="inquiry-email"
            name="email"
            type="email"
            autoComplete="email"
            maxLength={200}
            required
          />
          <p className={styles.hint}>We reply here. No newsletter.</p>
        </div>
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label htmlFor="inquiry-month">When do you want to travel?</label>
          <select className={styles.select} id="inquiry-month" name="travelMonth" required defaultValue="">
            <option value="" disabled>
              Choose a month
            </option>
            {months.map((month) => (
              <option key={month.value} value={month.value}>
                {month.label}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label htmlFor="inquiry-nights">Nights in Uzbekistan</label>
          <input
            className={styles.input}
            id="inquiry-nights"
            name="nights"
            type="number"
            inputMode="numeric"
            min={1}
            max={60}
            defaultValue={8}
            required
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="inquiry-travellers">Travellers</label>
          <input
            className={styles.input}
            id="inquiry-travellers"
            name="travellers"
            type="number"
            inputMode="numeric"
            min={1}
            max={20}
            defaultValue={2}
            required
          />
        </div>
      </div>

      <fieldset className={styles.fieldset}>
        <legend>What do you care about most?</legend>
        <div className={styles.choices}>
          {INTERESTS.map((interest) => (
            <label className={styles.choice} key={interest.value}>
              <input type="checkbox" name="interests" value={interest.value} />
              {interest.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.fieldset}>
        <legend>Comfort level</legend>
        <div className={styles.choices}>
          {COMFORT_LEVELS.map((level, index) => (
            <label className={styles.choice} key={level.value}>
              <input
                type="radio"
                name="comfort"
                value={level.value}
                defaultChecked={index === 1}
                required
              />
              {level.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className={styles.field}>
        <label htmlFor="inquiry-budget">Budget band</label>
        <select className={styles.select} id="inquiry-budget" name="budget" defaultValue="not-sure" required>
          {BUDGET_BANDS.map((band) => (
            <option key={band.value} value={band.value}>
              {band.label}
            </option>
          ))}
        </select>
        <p className={styles.hint}>
          Excluding international flights. A band is enough; we will show what
          each level buys.
        </p>
      </div>

      <div className={styles.field}>
        <label htmlFor="inquiry-message">Anything else?</label>
        <textarea
          className={styles.textarea}
          id="inquiry-message"
          name="message"
          maxLength={MESSAGE_MAX_LENGTH}
          placeholder="Cities you have in mind, mobility needs, dietary requirements, a fixed arrival flight, whether you have been before."
        />
      </div>

      <div className={styles.honeypot} aria-hidden="true">
        <label htmlFor="inquiry-website">Leave this field empty</label>
        <input
          id="inquiry-website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          defaultValue=""
        />
      </div>

      {status.kind === "error" ? (
        <p className={`${styles.status} ${styles.statusError}`} role="alert">
          {status.message}
        </p>
      ) : null}

      <div className={styles.actions}>
        <button
          className="btn btn-service"
          type="submit"
          disabled={status.kind === "submitting"}
        >
          {status.kind === "submitting" ? "Sending…" : "Send my inquiry"}
        </button>
        <p>
          Your details go only to Kebab Travel. See the{" "}
          <a href="/privacy#trip-inquiries">privacy policy</a>.
        </p>
      </div>
    </form>
  );
}
