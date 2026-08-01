"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import styles from "./review-console.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type ReviewStatus = "pending" | "in_review" | "approved" | "rejected" | "cancelled";
type ReviewDecision = "approve" | "reject";

type ReviewItem = {
  id: string;
  extraction_artifact_id: string;
  status: ReviewStatus;
  priority: number;
  assigned_principal_id: string | null;
  decision_reason: string | null;
  decided_at: string | null;
  updated_at: string;
};

type QueueItem = {
  review: ReviewItem;
  source_id: string;
  source_title: string;
  source_url: string;
  fetched_at: string;
  section_count: number;
};

type Artifact = {
  id: string;
  source_id: string;
  snapshot_id: string;
  adapter_key: string;
  media_type: string;
  raw_sha256: string;
  normalized_sha256: string;
  extracted_at: string;
  sections: Array<{ id: string; heading: string; body: string }>;
};

type Comparison = {
  current_artifact_id: string;
  previous_artifact_id: string | null;
  changed: boolean;
  changes: Array<{
    section_id: string;
    change_type: "added" | "removed" | "modified" | "unchanged";
    previous_heading: string | null;
    current_heading: string | null;
  }>;
};

type Principal = { id: string; roles: string[] };
type Envelope<T> = { data: T; meta: { request_id: string } };
type ErrorEnvelope = { error?: { code?: string; message?: string } };

const filters: Array<{ value: ReviewStatus; label: string }> = [
  { value: "pending", label: "Pending" },
  { value: "in_review", label: "In review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function compactId(value: string) {
  return `${value.slice(0, 8)}…${value.slice(-4)}`;
}

function reviewError(error: unknown) {
  return error instanceof Error ? error.message : "The review service could not complete the request.";
}

export default function ReviewConsole() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [status, setStatus] = useState<ReviewStatus>("pending");
  const [items, setItems] = useState<QueueItem[]>([]);
  const [selected, setSelected] = useState<QueueItem | null>(null);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [action, setAction] = useState<"claim" | ReviewDecision | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function request<T>(
    path: string,
    init?: RequestInit,
    bearerToken: string = token,
  ): Promise<T> {
      const response = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: {
          authorization: `Bearer ${bearerToken}`,
          "content-type": "application/json",
          "x-request-id": crypto.randomUUID(),
          ...init?.headers,
        },
      });
      const payload = (await response.json()) as Envelope<T> & ErrorEnvelope;
      if (!response.ok) {
        throw new Error(payload.error?.message ?? `Request failed with status ${response.status}.`);
      }
      return payload.data;
  }

  async function loadQueue(
    bearerToken: string = token,
    nextStatus: ReviewStatus = status,
  ) {
    if (!bearerToken) return;
    setLoading(true);
    setError("");
    try {
      const [identity, queue] = await Promise.all([
        request<Principal>("/auth/me", undefined, bearerToken),
        request<QueueItem[]>(
          `/admin/reviews?status=${nextStatus}&limit=50`,
          undefined,
          bearerToken,
        ),
      ]);
      setPrincipal(identity);
      setItems(queue);
      const nextSelected =
        queue.find((item) => item.review.id === selected?.review.id) ?? queue[0] ?? null;
      setSelected(nextSelected);
      await loadDetails(nextSelected, bearerToken);
    } catch (caught) {
      setPrincipal(null);
      setItems([]);
      setSelected(null);
      setError(reviewError(caught));
    } finally {
      setLoading(false);
    }
  }

  async function loadDetails(item: QueueItem | null, bearerToken: string = token) {
    if (!item || !bearerToken) {
      setArtifact(null);
      setComparison(null);
      return;
    }
    setDetailLoading(true);
    setError("");
    try {
      const [nextArtifact, nextComparison] = await Promise.all([
        request<Artifact>(
          `/admin/artifacts/${item.review.extraction_artifact_id}`,
          undefined,
          bearerToken,
        ),
        request<Comparison>(
          `/admin/artifacts/${item.review.extraction_artifact_id}/comparison`,
          undefined,
          bearerToken,
        ),
      ]);
      setArtifact(nextArtifact);
      setComparison(nextComparison);
    } catch (caught) {
      setArtifact(null);
      setComparison(null);
      setError(reviewError(caught));
    } finally {
      setDetailLoading(false);
    }
  }

  async function selectItem(item: QueueItem) {
    setSelected(item);
    await loadDetails(item);
  }

  async function selectStatus(nextStatus: ReviewStatus) {
    setStatus(nextStatus);
    await loadQueue(token, nextStatus);
  }

  const changedSections = useMemo(
    () => comparison?.changes.filter((change) => change.change_type !== "unchanged") ?? [],
    [comparison],
  );

  function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleaned = tokenInput.trim();
    if (!cleaned) return;
    setToken(cleaned);
    setMessage("Access token connected for this page session.");
    void loadQueue(cleaned, status);
  }

  function disconnect() {
    setToken("");
    setTokenInput("");
    setPrincipal(null);
    setItems([]);
    setSelected(null);
    setArtifact(null);
    setComparison(null);
    setMessage("Reviewer session disconnected.");
  }

  async function claim() {
    if (!selected) return;
    setAction("claim");
    setError("");
    try {
      const review = await request<ReviewItem>(`/admin/reviews/${selected.review.id}/claim`, {
        method: "POST",
      });
      const updated = { ...selected, review };
      setSelected(updated);
      setItems((current) =>
        current.map((item) => (item.review.id === review.id ? updated : item)),
      );
      setMessage("Review item claimed. Inspect the evidence before deciding.");
    } catch (caught) {
      setError(reviewError(caught));
    } finally {
      setAction(null);
    }
  }

  async function decide(decision: ReviewDecision) {
    if (!selected || !reason.trim()) return;
    setAction(decision);
    setError("");
    try {
      const review = await request<ReviewItem>(`/admin/reviews/${selected.review.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision, reason: reason.trim() }),
      });
      const updated = { ...selected, review };
      setSelected(updated);
      setItems((current) =>
        current.map((item) => (item.review.id === review.id ? updated : item)),
      );
      setReason("");
      setMessage(decision === "approve" ? "Extraction approved." : "Extraction rejected.");
    } catch (caught) {
      setError(reviewError(caught));
    } finally {
      setAction(null);
    }
  }

  const canDecide =
    selected?.review.status === "in_review" &&
    selected.review.assigned_principal_id === principal?.id;

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <Link className={styles.brand} href="/" aria-label="Uzbekistan OS home">
          <span className={styles.brandMark} aria-hidden="true">U</span>
          <span>
            <strong>Uzbekistan OS</strong>
            <small>Knowledge operations</small>
          </span>
        </Link>
        <div className={styles.session}>
          {principal ? (
            <span className={styles.identity} title={principal.id}>
              Reviewer {compactId(principal.id)}
            </span>
          ) : (
            <span className={styles.identity}>Not connected</span>
          )}
          {token && (
            <button className={styles.quietButton} type="button" onClick={disconnect}>
              Disconnect
            </button>
          )}
        </div>
      </header>

      {!token ? (
        <section className={styles.connectPanel} aria-labelledby="connect-title">
          <p className={styles.eyebrow}>Restricted workspace</p>
          <h1 id="connect-title">Connect a reviewer session</h1>
          <p>
            Enter a verified bearer token with the content reviewer or administrator role. The
            token stays in memory for this page session and is never added to the URL.
          </p>
          <form onSubmit={connect} className={styles.connectForm}>
            <label htmlFor="review-token">Bearer access token</label>
            <div>
              <input
                id="review-token"
                name="review-token"
                type="password"
                value={tokenInput}
                onChange={(event) => setTokenInput(event.target.value)}
                autoComplete="off"
                required
              />
              <button type="submit">Connect securely</button>
            </div>
          </form>
          <p className={styles.securityNote}>
            Production access remains disabled until an approved token-verifier adapter is
            configured.
          </p>
        </section>
      ) : (
        <div className={styles.workspace}>
          <aside className={styles.queuePanel} aria-labelledby="queue-title">
            <div className={styles.panelHeading}>
              <div>
                <p className={styles.eyebrow}>Review queue</p>
                <h1 id="queue-title">Evidence changes</h1>
              </div>
              <button
                className={styles.iconButton}
                type="button"
                onClick={() => void loadQueue(token, status)}
                aria-label="Refresh review queue"
                disabled={loading}
              >
                ↻
              </button>
            </div>

            <nav className={styles.filters} aria-label="Review status filters">
              {filters.map((filter) => (
                <button
                  key={filter.value}
                  type="button"
                  aria-pressed={status === filter.value}
                  onClick={() => void selectStatus(filter.value)}
                >
                  {filter.label}
                </button>
              ))}
            </nav>

            <div className={styles.queueList} aria-busy={loading}>
              {loading ? (
                <QueueSkeleton />
              ) : items.length ? (
                items.map((item) => (
                  <button
                    className={styles.queueItem}
                    data-selected={selected?.review.id === item.review.id}
                    key={item.review.id}
                    type="button"
                    onClick={() => void selectItem(item)}
                  >
                    <span className={styles.queueMeta}>
                      <StatusPill status={item.review.status} />
                      <span>Priority {item.review.priority}</span>
                    </span>
                    <strong>{item.source_title}</strong>
                    <span>{item.section_count} sections · {formatDate(item.fetched_at)}</span>
                  </button>
                ))
              ) : (
                <div className={styles.emptyState}>
                  <span aria-hidden="true">✓</span>
                  <strong>No {status.replace("_", " ")} items</strong>
                  <p>The queue is clear for this status.</p>
                </div>
              )}
            </div>
          </aside>

          <section className={styles.documentPanel} aria-labelledby="document-title">
            {selected ? (
              <>
                <div className={styles.documentHeader}>
                  <div>
                    <p className={styles.eyebrow}>Extracted evidence</p>
                    <h2 id="document-title">{selected.source_title}</h2>
                    <a href={selected.source_url} target="_blank" rel="noreferrer">
                      Open official source <span aria-hidden="true">↗</span>
                    </a>
                  </div>
                  <StatusPill status={selected.review.status} />
                </div>

                {detailLoading ? (
                  <DocumentSkeleton />
                ) : artifact ? (
                  <div className={styles.sections}>
                    {artifact.sections.map((section, index) => {
                      const change = comparison?.changes.find(
                        (item) => item.section_id === section.id,
                      );
                      return (
                        <article className={styles.sectionCard} key={section.id}>
                          <div className={styles.sectionIndex}>{String(index + 1).padStart(2, "0")}</div>
                          <div>
                            <div className={styles.sectionTitle}>
                              <h3>{section.heading}</h3>
                              {change && change.change_type !== "unchanged" && (
                                <span data-change={change.change_type}>{change.change_type}</span>
                              )}
                            </div>
                            <p>{section.body}</p>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <div className={styles.emptyState}>Select an item to load its evidence.</div>
                )}
              </>
            ) : (
              <div className={styles.blankDocument}>
                <span aria-hidden="true">◎</span>
                <h2 id="document-title">Choose a review item</h2>
                <p>Its checksum-verified extraction and source lineage will appear here.</p>
              </div>
            )}
          </section>

          <aside className={styles.inspector} aria-labelledby="inspector-title">
            <p className={styles.eyebrow}>Evidence inspector</p>
            <h2 id="inspector-title">Review controls</h2>

            {selected && artifact ? (
              <>
                <dl className={styles.metadata}>
                  <div><dt>Fetched</dt><dd>{formatDate(selected.fetched_at)}</dd></div>
                  <div><dt>Adapter</dt><dd>{artifact.adapter_key}</dd></div>
                  <div><dt>Media</dt><dd>{artifact.media_type}</dd></div>
                  <div><dt>Changes</dt><dd>{changedSections.length}</dd></div>
                  <div><dt>Raw SHA-256</dt><dd><code title={artifact.raw_sha256}>{compactId(artifact.raw_sha256)}</code></dd></div>
                </dl>

                <div className={styles.changeSummary}>
                  <h3>Compared with prior approval</h3>
                  {comparison?.previous_artifact_id ? (
                    changedSections.length ? (
                      <ul>
                        {changedSections.map((change) => (
                          <li key={change.section_id}>
                            <span data-change={change.change_type}>{change.change_type}</span>
                            {change.current_heading ?? change.previous_heading ?? change.section_id}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No section changes detected.</p>
                    )
                  ) : (
                    <p>This is the first reviewed extraction for this source.</p>
                  )}
                </div>

                {selected.review.status === "pending" ? (
                  <button
                    className={styles.primaryButton}
                    type="button"
                    onClick={() => void claim()}
                    disabled={action !== null}
                  >
                    {action === "claim" ? "Claiming…" : "Claim review"}
                  </button>
                ) : canDecide ? (
                  <div className={styles.decisionForm}>
                    <label htmlFor="decision-reason">Decision reason</label>
                    <textarea
                      id="decision-reason"
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      maxLength={2000}
                      placeholder="Summarize the evidence checked and any concerns."
                      rows={5}
                    />
                    <span>{reason.length}/2000</span>
                    <div>
                      <button
                        className={styles.rejectButton}
                        type="button"
                        disabled={!reason.trim() || action !== null}
                        onClick={() => void decide("reject")}
                      >
                        {action === "reject" ? "Rejecting…" : "Reject"}
                      </button>
                      <button
                        className={styles.primaryButton}
                        type="button"
                        disabled={!reason.trim() || action !== null}
                        onClick={() => void decide("approve")}
                      >
                        {action === "approve" ? "Approving…" : "Approve"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className={styles.lockedNote}>
                    {selected.review.status === "in_review"
                      ? "This item is assigned to another reviewer."
                      : `This review is ${selected.review.status}.`}
                  </p>
                )}
              </>
            ) : (
              <p className={styles.inspectorPlaceholder}>
                Select a queue item to inspect its source, changes, and decision controls.
              </p>
            )}
          </aside>
        </div>
      )}

      <div className={styles.announcer} aria-live="polite" aria-atomic="true">
        {error || message}
      </div>
      {error && (
        <div className={styles.errorBanner} role="alert">
          <strong>Review service unavailable</strong>
          <span>{error}</span>
          <button type="button" onClick={() => setError("")} aria-label="Dismiss error">×</button>
        </div>
      )}
    </main>
  );
}

function StatusPill({ status }: { status: ReviewStatus }) {
  return <span className={styles.statusPill} data-status={status}>{status.replace("_", " ")}</span>;
}

function QueueSkeleton() {
  return (
    <div className={styles.skeletonList} aria-label="Loading review queue">
      {[0, 1, 2].map((item) => <span key={item} />)}
    </div>
  );
}

function DocumentSkeleton() {
  return (
    <div className={styles.documentSkeleton} aria-label="Loading extracted evidence">
      {[0, 1, 2].map((item) => <span key={item} />)}
    </div>
  );
}
