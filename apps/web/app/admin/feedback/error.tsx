"use client";

import Link from "next/link";
import { useEffect } from "react";
import styles from "./feedback-dashboard.module.css";

export default function FeedbackError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Feedback dashboard failed", error.name, error.digest);
  }, [error]);

  return (
    <main className={styles.page}>
      <section className={styles.errorState}>
        <p className={styles.eyebrow}>Feedback review</p>
        <h1>The review queue is temporarily unavailable</h1>
        <p>No reports were changed. Try loading the queue again.</p>
        <div className={styles.errorActions}>
          <button
            className={styles.primaryButton}
            onClick={reset}
            type="button"
          >
            Try again
          </button>
          <Link className={styles.secondaryLink} href="/account">
            Return to account
          </Link>
        </div>
      </section>
    </main>
  );
}
