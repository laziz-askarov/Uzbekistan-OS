"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import type { StaffIdentity } from "@/lib/admin-auth";
import type {
  FeedbackFilters,
  FeedbackItem,
  FeedbackPageData,
  FeedbackStatus,
  StaffOption,
} from "@/lib/admin-feedback";
import styles from "./feedback-dashboard.module.css";

const feedbackCategories = [
  "incorrect",
  "outdated",
  "unclear",
  "other",
] as const;
const feedbackStatuses = ["new", "reviewing", "resolved", "dismissed"] as const;

type DashboardProps = {
  data: FeedbackPageData;
  filters: FeedbackFilters;
  identity: StaffIdentity;
};

const categoryLabels = {
  incorrect: "Incorrect",
  outdated: "Outdated",
  unclear: "Unclear",
  other: "Other",
} as const;

const statusLabels = {
  new: "New",
  reviewing: "In review",
  resolved: "Resolved",
  dismissed: "Dismissed",
} as const;

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function staffLabel(staff: StaffOption) {
  return (
    staff.name || staff.email || `${staff.role} · ${staff.userId.slice(0, 8)}`
  );
}

function filterQuery(filters: FeedbackFilters, page: number) {
  const query = new URLSearchParams();
  if (filters.category) query.set("category", filters.category);
  if (filters.status) query.set("status", filters.status);
  if (filters.dateFrom) query.set("from", filters.dateFrom);
  if (filters.dateTo) query.set("to", filters.dateTo);
  if (page > 1) query.set("page", String(page));
  const value = query.toString();
  return value ? `/admin/feedback?${value}` : "/admin/feedback";
}

function FeedbackReviewCard({
  identity,
  item,
  staff,
}: {
  identity: StaffIdentity;
  item: FeedbackItem;
  staff: StaffOption[];
}) {
  const router = useRouter();
  const [adminNotes, setAdminNotes] = useState(item.adminNotes ?? "");
  const [assignedTo, setAssignedTo] = useState(item.assignee?.userId ?? "");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const closed = item.status === "resolved" || item.status === "dismissed";
  const isAdmin = identity.role === "admin";
  const canEdit = isAdmin || !closed;
  const feedbackId = `feedback-${item.id}`;

  async function updateReport(nextStatus: FeedbackStatus) {
    setPending(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/admin/feedback/${item.id}`, {
        method: "PATCH",
        headers: {
          "content-type": "application/json",
          "x-request-id": crypto.randomUUID(),
        },
        body: JSON.stringify({
          adminNotes: adminNotes.trim() || null,
          assignedTo: isAdmin ? assignedTo || null : identity.userId,
          status: nextStatus,
        }),
      });
      const result = (await response.json().catch(() => null)) as {
        message?: string;
      } | null;
      if (!response.ok) {
        throw new Error(result?.message || "The report could not be updated.");
      }
      setNotice("Review update saved.");
      router.refresh();
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "The report could not be updated.",
      );
    } finally {
      setPending(false);
    }
  }

  function saveCurrent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void updateReport(item.status);
  }

  return (
    <article className={styles.reportCard} aria-labelledby={feedbackId}>
      <header className={styles.reportHeader}>
        <div>
          <div className={styles.badges}>
            <span className={`${styles.badge} ${styles[item.category]}`}>
              {categoryLabels[item.category]}
            </span>
            <span className={`${styles.badge} ${styles[item.status]}`}>
              {statusLabels[item.status]}
            </span>
          </div>
          <h2 id={feedbackId}>Reported assistant guidance</h2>
        </div>
        <time dateTime={item.createdAt}>{displayDate(item.createdAt)}</time>
      </header>

      <div className={styles.reportGrid}>
        <section aria-label="Reported response">
          <p className={styles.fieldLabel}>Assistant response</p>
          <div className={styles.responseText}>{item.responseText}</div>
        </section>
        <section aria-label="Customer report">
          <p className={styles.fieldLabel}>Customer context</p>
          <p className={styles.reporter}>
            {item.reporter.name ||
              `Customer ${item.reporter.userId.slice(0, 8)}`}
          </p>
          <p className={styles.details}>
            {item.details || "No additional details were provided."}
          </p>
        </section>
      </div>

      <form className={styles.reviewForm} onSubmit={saveCurrent}>
        <div className={styles.workflowFields}>
          {isAdmin ? (
            <label>
              Assigned reviewer
              <select
                disabled={pending}
                onChange={(event) => setAssignedTo(event.target.value)}
                value={assignedTo}
              >
                <option value="">Unassigned</option>
                {staff.map((option) => (
                  <option key={option.userId} value={option.userId}>
                    {staffLabel(option)} ({option.role})
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <div>
              <p className={styles.fieldLabel}>Assigned reviewer</p>
              <p className={styles.assignment}>Assigned to you</p>
            </div>
          )}
          <label>
            Internal notes
            <textarea
              disabled={pending || !canEdit}
              maxLength={4000}
              onChange={(event) => setAdminNotes(event.target.value)}
              placeholder="Record the evidence checked and the reason for the decision."
              rows={4}
              value={adminNotes}
            />
          </label>
        </div>

        <div className={styles.actionRow}>
          {canEdit ? (
            <button
              className={styles.secondaryButton}
              disabled={pending}
              type="submit"
            >
              Save changes
            </button>
          ) : null}
          {!closed && item.status === "new" ? (
            <button
              className={styles.secondaryButton}
              disabled={pending}
              onClick={() => void updateReport("reviewing")}
              type="button"
            >
              Start review
            </button>
          ) : null}
          {!closed ? (
            <>
              <button
                className={styles.secondaryButton}
                disabled={pending}
                onClick={() => void updateReport("dismissed")}
                type="button"
              >
                Dismiss
              </button>
              <button
                className={styles.primaryButton}
                disabled={pending}
                onClick={() => void updateReport("resolved")}
                type="button"
              >
                Resolve
              </button>
            </>
          ) : isAdmin ? (
            <button
              className={styles.primaryButton}
              disabled={pending}
              onClick={() => void updateReport("reviewing")}
              type="button"
            >
              Reopen report
            </button>
          ) : null}
        </div>
        <div className={styles.formStatus} aria-live="polite">
          {pending ? "Saving…" : error || notice}
        </div>
      </form>

      <footer className={styles.reportFooter}>
        <span>Report {item.id.slice(0, 8)}</span>
        <span>Updated {displayDate(item.updatedAt)}</span>
        {item.reviewer ? (
          <span>Closed by {staffLabel(item.reviewer)}</span>
        ) : null}
      </footer>
    </article>
  );
}

export default function FeedbackDashboard({
  data,
  filters,
  identity,
}: DashboardProps) {
  const pageCount = Math.max(1, Math.ceil(data.total / data.pageSize));

  return (
    <main className={styles.page}>
      <header className={styles.topbar}>
        <div>
          <Link className={styles.brand} href="/">
            Uzbekistan OS
          </Link>
          <span className={styles.workspaceLabel}>Feedback review</span>
        </div>
        <div className={styles.identity}>
          {identity.role === "admin" ? (
            <Link href="/admin/content">Content</Link>
          ) : null}
          <span>{identity.email || identity.userId.slice(0, 8)}</span>
          <span className={styles.role}>{identity.role}</span>
          <Link href="/account">Account</Link>
        </div>
      </header>

      <section className={styles.content}>
        <div className={styles.heading}>
          <div>
            <p className={styles.eyebrow}>Quality operations</p>
            <h1>Customer feedback</h1>
            <p>
              Review reports against current official evidence and keep an
              auditable record of each decision.
            </p>
          </div>
          <div className={styles.total}>
            <strong>{data.total}</strong>
            <span>matching reports</span>
          </div>
        </div>

        <form className={styles.filters} method="get">
          <label>
            Report type
            <select defaultValue={filters.category ?? ""} name="category">
              <option value="">All types</option>
              {feedbackCategories.map((category) => (
                <option key={category} value={category}>
                  {categoryLabels[category]}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status
            <select defaultValue={filters.status ?? ""} name="status">
              <option value="">All statuses</option>
              {feedbackStatuses.map((status) => (
                <option key={status} value={status}>
                  {statusLabels[status]}
                </option>
              ))}
            </select>
          </label>
          <label>
            From
            <input
              defaultValue={filters.dateFrom ?? ""}
              name="from"
              type="date"
            />
          </label>
          <label>
            To
            <input defaultValue={filters.dateTo ?? ""} name="to" type="date" />
          </label>
          <button className={styles.filterButton} type="submit">
            Apply filters
          </button>
          <Link className={styles.clearLink} href="/admin/feedback">
            Clear
          </Link>
        </form>

        {data.items.length ? (
          <div className={styles.reportList}>
            {data.items.map((item) => (
              <FeedbackReviewCard
                identity={identity}
                item={item}
                key={`${item.id}-${item.updatedAt}`}
                staff={data.staff}
              />
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>
            <h2>No reports match these filters</h2>
            <p>Try a different date range, category, or workflow status.</p>
          </div>
        )}

        {pageCount > 1 ? (
          <nav className={styles.pagination} aria-label="Feedback pages">
            {data.page > 1 ? (
              <Link href={filterQuery(filters, data.page - 1)}>Previous</Link>
            ) : (
              <span aria-disabled="true">Previous</span>
            )}
            <span>
              Page {data.page} of {pageCount}
            </span>
            {data.page < pageCount ? (
              <Link href={filterQuery(filters, data.page + 1)}>Next</Link>
            ) : (
              <span aria-disabled="true">Next</span>
            )}
          </nav>
        ) : null}
      </section>
    </main>
  );
}
