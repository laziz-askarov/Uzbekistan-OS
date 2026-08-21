"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { useAdminApiSession } from "@/lib/admin-api-session";
import { ThemeToggle } from "../design-system/theme-toggle";
import styles from "./operations-dashboard.module.css";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const API_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_API_BASE_URL);
const MAX_UPLOAD_BYTES = 10_000_000;

type Principal = { id: string; roles: string[] };

type AdminSource = {
  id: string;
  slug: string;
  organization: string;
  title: string;
  url: string;
  source_type: "html" | "pdf" | "feed" | "manual";
  domains: string[];
  languages: string[];
  crawl_policy: "allowed" | "manual_only" | "blocked" | "pending_review";
  adapter_key: string;
  trust_tier: number;
  registry_status: "draft" | "approved" | "rejected";
  active: boolean;
  production_eligible: boolean;
  automatic_fetch_eligible: boolean;
  manual_upload_eligible: boolean;
  schedule_interval_minutes: number | null;
  last_verified_at: string | null;
  latest_job_status: JobStatus | null;
};

type JobStatus =
  | "queued"
  | "running"
  | "retry_scheduled"
  | "succeeded"
  | "dead_lettered"
  | "cancelled";

type IngestionJob = {
  id: string;
  source_id: string;
  source_title: string;
  idempotency_key: string;
  status: JobStatus;
  attempt_count: number;
  max_attempts: number;
  scheduled_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
};

type UploadResult = {
  source_id: string;
  filename: string;
  status: "changed" | "unchanged";
  snapshot_id: string | null;
  extraction_artifact_id: string | null;
  review_item_id: string | null;
};

type Envelope<T> = { data: T; meta: { request_id: string } };
type ErrorEnvelope = { error?: { code?: string; message?: string } };

type WebHealth = {
  commit: string;
  service: string;
  status: "ok";
  version: string;
};

type ApiHealth = {
  environment: string;
  service: string;
  status: "ok";
  version: string;
};

type ApiReadiness = {
  checks: Record<string, string>;
  service: string;
  status: "ready";
};

type SystemCheck = {
  detail: string;
  label: string;
  status: "healthy" | "degraded" | "unavailable";
};

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "The ingestion service could not complete this request.";
}

function formatDate(value: string | null) {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function compactId(value: string) {
  return `${value.slice(0, 8)}…${value.slice(-4)}`;
}

function durationSeconds(job: IngestionJob) {
  if (!job.started_at || !job.completed_at) return null;
  return Math.max(
    0,
    Math.round(
      (new Date(job.completed_at).getTime() -
        new Date(job.started_at).getTime()) /
        1000,
    ),
  );
}

function sourceTypeLabel(value: AdminSource["source_type"]) {
  return value === "pdf" ? "PDF" : value.replace("_", " ");
}

function inferredContentType(file: File) {
  if (file.type) return file.type;
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (extension === "pdf") return "application/pdf";
  if (extension === "html" || extension === "htm") return "text/html";
  if (extension === "txt") return "text/plain";
  return "application/octet-stream";
}

function fileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () =>
      reject(new Error("The selected file could not be read."));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string" || !result.includes(",")) {
        reject(new Error("The selected file could not be encoded."));
        return;
      }
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.readAsDataURL(file);
  });
}

export default function OperationsDashboard() {
  const adminSession = useAdminApiSession();
  const token = adminSession.accessToken ?? "";
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [sources, setSources] = useState<AdminSource[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [uploadSource, setUploadSource] = useState<AdminSource | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [systemChecks, setSystemChecks] = useState<SystemCheck[]>([]);
  const [healthCheckedAt, setHealthCheckedAt] = useState<string | null>(null);

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
      throw new Error(
        payload.error?.message ??
          `Request failed with status ${response.status}.`,
      );
    }
    return payload.data;
  }

  async function publicRequest<T>(url: string): Promise<T> {
    const response = await fetch(url, {
      cache: "no-store",
      headers: { "x-request-id": crypto.randomUUID() },
    });
    const payload = (await response.json()) as Envelope<T> & ErrorEnvelope;
    if (!response.ok) {
      throw new Error(
        payload.error?.message ??
          `Health request failed with status ${response.status}.`,
      );
    }
    return payload.data;
  }

  async function loadSystemHealth() {
    const [web] = await Promise.allSettled([
      publicRequest<WebHealth>("/api/health"),
    ]);
    const checks: SystemCheck[] = [];
    checks.push(
      web.status === "fulfilled"
        ? {
            label: "Web application",
            status: "healthy",
            detail: `Version ${web.value.version} · commit ${web.value.commit}`,
          }
        : {
            label: "Web application",
            status: "unavailable",
            detail: "The web health endpoint did not respond.",
          },
    );

    if (!API_CONFIGURED) {
      checks.push({
        label: "Guidance API",
        status: "degraded",
        detail:
          "NEXT_PUBLIC_API_BASE_URL is not configured for this deployment.",
      });
    } else {
      const [api, readiness] = await Promise.allSettled([
        publicRequest<ApiHealth>(`${API_BASE}/health`),
        publicRequest<ApiReadiness>(`${API_BASE}/ready`),
      ]);
      checks.push(
        api.status === "fulfilled"
          ? {
              label: "Guidance API",
              status: "healthy",
              detail: `${api.value.environment} · version ${api.value.version}`,
            }
          : {
              label: "Guidance API",
              status: "unavailable",
              detail: "The API health endpoint could not be reached.",
            },
      );
      if (readiness.status === "fulfilled") {
        for (const [dependency, status] of Object.entries(
          readiness.value.checks,
        )) {
          checks.push({
            label: dependency.replaceAll("_", " "),
            status: status === "ok" ? "healthy" : "degraded",
            detail:
              status === "ok"
                ? "Dependency check passed."
                : `Dependency reported ${status}.`,
          });
        }
      } else {
        checks.push({
          label: "API dependencies",
          status: "unavailable",
          detail: "Readiness checks are unavailable.",
        });
      }
    }
    setSystemChecks(checks);
    setHealthCheckedAt(new Date().toISOString());
  }

  async function loadOperations(bearerToken: string = token) {
    if (!bearerToken) return;
    setBusy(true);
    setError("");
    const healthRequest = loadSystemHealth();
    try {
      const [identity, nextSources, nextJobs] = await Promise.all([
        request<Principal>("/auth/me", undefined, bearerToken),
        request<AdminSource[]>("/admin/sources", undefined, bearerToken),
        request<IngestionJob[]>(
          "/admin/ingestion/jobs?limit=50",
          undefined,
          bearerToken,
        ),
      ]);
      if (!identity.roles.includes("admin")) {
        throw new Error("This dashboard requires the administrator role.");
      }
      setPrincipal(identity);
      setSources(nextSources);
      setJobs(nextJobs);
    } catch (caught) {
      setPrincipal(null);
      setSources([]);
      setJobs([]);
      setError(errorMessage(caught));
    } finally {
      await healthRequest;
      setBusy(false);
    }
  }

  useEffect(() => {
    const accessToken = adminSession.accessToken;
    if (adminSession.loading || !accessToken) return;
    void Promise.resolve().then(() => {
      setMessage("");
      return loadOperations(accessToken);
    });
    // This bootstrap should rerun only when the authenticated session changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminSession.accessToken, adminSession.error, adminSession.loading]);

  const connectionError =
    error ||
    (!adminSession.loading && !adminSession.accessToken
      ? (adminSession.error ?? "Administrator authentication is required.")
      : "");

  async function runCrawler(source: AdminSource) {
    setActiveAction(`crawl:${source.id}`);
    setError("");
    setMessage("");
    try {
      const job = await request<IngestionJob>("/admin/ingestion/jobs", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ source_id: source.id, max_attempts: 3 }),
      });
      setJobs((current) => [
        job,
        ...current.filter((item) => item.id !== job.id),
      ]);
      setMessage(
        `Crawler job ${compactId(job.id)} queued for ${source.title}.`,
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setActiveAction(null);
    }
  }

  function startUpload(source: AdminSource) {
    setUploadSource(source);
    setUploadFile(null);
    setError("");
    setMessage("");
  }

  async function uploadEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadSource || !uploadFile) return;
    if (uploadFile.size > MAX_UPLOAD_BYTES) {
      setError("The selected document exceeds the 10 MB upload limit.");
      return;
    }
    setActiveAction(`upload:${uploadSource.id}`);
    setError("");
    setMessage("");
    try {
      const contentType = inferredContentType(uploadFile);
      const contentBase64 = await fileAsBase64(uploadFile);
      const result = await request<UploadResult>(
        `/admin/sources/${uploadSource.id}/uploads`,
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID() },
          body: JSON.stringify({
            filename: uploadFile.name,
            content_type: contentType,
            content_base64: contentBase64,
            max_attempts: 1,
          }),
        },
      );
      setMessage(
        result.status === "changed"
          ? `${result.filename} was secured, extracted, and sent to review.`
          : `${result.filename} matches the latest source snapshot; no duplicate review was created.`,
      );
      setUploadSource(null);
      setUploadFile(null);
      const nextJobs = await request<IngestionJob[]>(
        "/admin/ingestion/jobs?limit=50",
      );
      setJobs(nextJobs);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setActiveAction(null);
    }
  }

  const filteredSources = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return sources;
    return sources.filter((source) =>
      [
        source.title,
        source.organization,
        source.slug,
        ...source.domains,
        ...source.languages,
      ].some((value) => value.toLowerCase().includes(normalized)),
    );
  }, [query, sources]);

  const analytics = useMemo(() => {
    const terminalJobs = jobs.filter((job) =>
      ["succeeded", "dead_lettered", "cancelled"].includes(job.status),
    );
    const successfulJobs = jobs.filter(
      (job) => job.status === "succeeded",
    ).length;
    const durations = jobs
      .map(durationSeconds)
      .filter((value): value is number => value !== null);
    const incidents = jobs.filter(
      (job) =>
        Boolean(job.error_code || job.error_message) ||
        ["retry_scheduled", "dead_lettered", "cancelled"].includes(job.status),
    );
    const statusCounts = (
      [
        "succeeded",
        "running",
        "queued",
        "retry_scheduled",
        "dead_lettered",
        "cancelled",
      ] as JobStatus[]
    ).map((status) => ({
      count: jobs.filter((job) => job.status === status).length,
      status,
    }));
    return {
      active: sources.filter((source) => source.active).length,
      scheduled: sources.filter(
        (source) => source.schedule_interval_minutes !== null,
      ).length,
      successfulJobs,
      successRate: terminalJobs.length
        ? Math.round((successfulJobs / terminalJobs.length) * 100)
        : null,
      averageDuration: durations.length
        ? Math.round(
            durations.reduce((total, value) => total + value, 0) /
              durations.length,
          )
        : null,
      inFlight: jobs.filter((job) =>
        ["queued", "running", "retry_scheduled"].includes(job.status),
      ).length,
      incidents,
      statusCounts,
      sourceWarnings: sources.filter(
        (source) =>
          !source.active ||
          !source.last_verified_at ||
          source.latest_job_status === "dead_lettered" ||
          source.latest_job_status === "retry_scheduled",
      ),
    };
  }, [jobs, sources]);

  if (!principal) {
    return (
      <main className={styles.shell}>
        <header className={styles.topbar}>
          <Brand />
          <ThemeToggle className={styles.themeButton} />
        </header>
        <section
          className={styles.connectPanel}
          aria-labelledby="connect-title"
        >
          <p className={styles.eyebrow}>Restricted operations</p>
          <h1 id="connect-title">Manage trusted knowledge sources.</h1>
          <p>
            {adminSession.loading || busy
              ? "Connecting your signed-in administrator session…"
              : "Your signed-in account could not open the ingestion workspace."}
          </p>
          <p className={styles.securityNote}>
            Access uses your short-lived Supabase session in memory and is
            verified again by the guidance API.
          </p>
          {connectionError ? (
            <p className={styles.error} role="alert">
              {connectionError}
            </p>
          ) : null}
          {message ? (
            <p className={styles.notice} role="status">
              {message}
            </p>
          ) : null}
          {!adminSession.loading && !busy ? (
            <Link className={styles.secondaryButton} href="/account">
              Return to account
            </Link>
          ) : null}
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <Brand />
        <nav className={styles.topActions} aria-label="Admin utilities">
          <a href="#analytics">Analytics</a>
          <Link href="/admin/reviews">Review queue</Link>
          <Link href="/admin/feedback">Feedback</Link>
          <ThemeToggle className={styles.themeButton} />
          <Link className={styles.quietButton} href="/account">
            Account
          </Link>
        </nav>
      </header>

      <div className={styles.page}>
        <section className={styles.hero}>
          <div>
            <p className={styles.eyebrow}>Knowledge operations</p>
            <h1>Ingestion control center</h1>
            <p>
              Curate official evidence, operate allowlisted crawlers, and follow
              every job into the human review queue.
            </p>
          </div>
          <button
            className={styles.refreshButton}
            disabled={busy}
            onClick={() => void loadOperations()}
            type="button"
          >
            <span aria-hidden="true">↻</span> {busy ? "Refreshing…" : "Refresh"}
          </button>
        </section>

        <section className={styles.stats} aria-label="Ingestion summary">
          <Stat
            label="Active sources"
            value={analytics.active}
            detail={`${sources.length} configured`}
          />
          <Stat
            label="Success rate"
            value={
              analytics.successRate === null ? "—" : `${analytics.successRate}%`
            }
            detail={`${analytics.successfulJobs} successful jobs`}
          />
          <Stat
            label="In progress"
            value={analytics.inFlight}
            detail="Queued, running, or retrying"
          />
          <Stat
            label="Open incidents"
            value={analytics.incidents.length}
            detail="Recent operational errors"
            attention={analytics.incidents.length > 0}
          />
        </section>

        <section
          className={styles.section}
          id="analytics"
          aria-labelledby="analytics-heading"
        >
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.eyebrow}>System analytics</p>
              <h2 id="analytics-heading">Operational health</h2>
            </div>
            <span className={styles.jobCount}>
              {healthCheckedAt
                ? `Checked ${formatDate(healthCheckedAt)}`
                : "Not checked"}
            </span>
          </div>

          <div className={styles.healthGrid} aria-label="Service health">
            {systemChecks.map((check) => (
              <article
                className={styles.healthCard}
                data-status={check.status}
                key={check.label}
              >
                <span className={styles.healthIndicator} aria-hidden="true" />
                <div>
                  <strong>{check.label}</strong>
                  <p>{check.detail}</p>
                </div>
                <span className={styles.healthStatus}>{check.status}</span>
              </article>
            ))}
          </div>

          <div className={styles.analyticsGrid}>
            <article className={styles.analyticsPanel}>
              <div className={styles.panelHeading}>
                <div>
                  <h3>Job outcomes</h3>
                  <p>Distribution across the latest {jobs.length} jobs.</p>
                </div>
                <strong>
                  {analytics.averageDuration === null
                    ? "—"
                    : `${analytics.averageDuration}s`}
                  <small>average duration</small>
                </strong>
              </div>
              <div
                className={styles.outcomeChart}
                role="img"
                aria-label={analytics.statusCounts
                  .map((item) => `${item.status}: ${item.count}`)
                  .join(", ")}
              >
                {analytics.statusCounts.map((item) => (
                  <div className={styles.outcomeRow} key={item.status}>
                    <span>{item.status.replace("_", " ")}</span>
                    <div className={styles.outcomeTrack}>
                      <span
                        data-status={item.status}
                        style={{
                          width: `${jobs.length ? Math.max(4, (item.count / jobs.length) * 100) : 0}%`,
                        }}
                      />
                    </div>
                    <strong>{item.count}</strong>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.analyticsPanel}>
              <div className={styles.panelHeading}>
                <div>
                  <h3>Recent incidents</h3>
                  <p>Retries, failed jobs, and reported crawler errors.</p>
                </div>
                <span
                  className={styles.incidentCount}
                  data-clear={analytics.incidents.length === 0}
                >
                  {analytics.incidents.length}
                </span>
              </div>
              {analytics.incidents.length ? (
                <ul className={styles.incidentList}>
                  {analytics.incidents.slice(0, 5).map((incident) => (
                    <li key={incident.id}>
                      <div>
                        <strong>{incident.source_title}</strong>
                        <span>
                          {formatDate(
                            incident.completed_at ?? incident.scheduled_at,
                          )}
                        </span>
                      </div>
                      <p>
                        {incident.error_message ??
                          `Job entered ${incident.status.replace("_", " ")} state.`}
                      </p>
                      {incident.error_code ? (
                        <code>{incident.error_code}</code>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className={styles.clearState}>
                  <strong>No recent ingestion errors</strong>
                  <span>The latest operational window is clear.</span>
                </div>
              )}
            </article>
          </div>

          {analytics.sourceWarnings.length ? (
            <div className={styles.sourceWarning} role="status">
              <strong>
                {analytics.sourceWarnings.length} source records need review.
              </strong>
              <span>
                Inactive, unverified, retrying, or failed sources are included.
              </span>
            </div>
          ) : null}
        </section>

        <div className={styles.feedback} aria-live="polite">
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}
          {message ? (
            <p className={styles.notice} role="status">
              {message}
            </p>
          ) : null}
        </div>

        {uploadSource ? (
          <section
            className={styles.uploadPanel}
            aria-labelledby="upload-heading"
          >
            <div>
              <p className={styles.eyebrow}>Manual evidence</p>
              <h2 id="upload-heading">Upload for {uploadSource.title}</h2>
              <p>
                Accepted: PDF, HTML, XHTML, or plain text. Maximum 10 MB. The
                file is checksum-verified, stored as source evidence, and queued
                for review.
              </p>
            </div>
            <form onSubmit={uploadEvidence}>
              <label className={styles.filePicker} htmlFor="evidence-file">
                <span>
                  {uploadFile ? uploadFile.name : "Choose official document"}
                </span>
                <small>
                  {uploadFile
                    ? `${Math.ceil(uploadFile.size / 1024)} KB`
                    : "PDF, HTML, or TXT"}
                </small>
              </label>
              <input
                accept=".pdf,.html,.htm,.txt,application/pdf,text/html,application/xhtml+xml,text/plain"
                className={styles.visuallyHidden}
                id="evidence-file"
                onChange={(event) =>
                  setUploadFile(event.target.files?.[0] ?? null)
                }
                type="file"
              />
              <div className={styles.formActions}>
                <button
                  className={styles.quietButton}
                  onClick={() => {
                    setUploadSource(null);
                    setUploadFile(null);
                  }}
                  type="button"
                >
                  Cancel
                </button>
                <button
                  className={styles.primaryButton}
                  disabled={
                    !uploadFile || activeAction === `upload:${uploadSource.id}`
                  }
                  type="submit"
                >
                  {activeAction === `upload:${uploadSource.id}`
                    ? "Processing…"
                    : "Upload and process"}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className={styles.section} aria-labelledby="sources-heading">
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.eyebrow}>Source registry</p>
              <h2 id="sources-heading">Official sources</h2>
            </div>
            <label className={styles.search}>
              <span className={styles.visuallyHidden}>Search sources</span>
              <span aria-hidden="true">⌕</span>
              <input
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search sources"
                type="search"
                value={query}
              />
            </label>
          </div>

          <div className={styles.sourceGrid}>
            {filteredSources.map((source) => (
              <article className={styles.sourceCard} key={source.id}>
                <div className={styles.sourceHeader}>
                  <div
                    className={styles.sourceIcon}
                    data-type={source.source_type}
                    aria-hidden="true"
                  >
                    {source.source_type === "pdf" ? "PDF" : "WWW"}
                  </div>
                  <div>
                    <div className={styles.pills}>
                      <span
                        data-tone={
                          source.registry_status === "approved"
                            ? "success"
                            : "neutral"
                        }
                      >
                        {source.registry_status}
                      </span>
                      <span>{sourceTypeLabel(source.source_type)}</span>
                    </div>
                    <h3>{source.title}</h3>
                    <p>{source.organization}</p>
                  </div>
                </div>
                <dl className={styles.sourceMeta}>
                  <div>
                    <dt>Domains</dt>
                    <dd>{source.domains.join(", ")}</dd>
                  </div>
                  <div>
                    <dt>Languages</dt>
                    <dd>
                      {source.languages
                        .map((item) => item.toUpperCase())
                        .join(", ")}
                    </dd>
                  </div>
                  <div>
                    <dt>Policy</dt>
                    <dd>{source.crawl_policy.replace("_", " ")}</dd>
                  </div>
                  <div>
                    <dt>Verified</dt>
                    <dd>{formatDate(source.last_verified_at)}</dd>
                  </div>
                </dl>
                <a
                  className={styles.sourceLink}
                  href={source.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  View official source <span aria-hidden="true">↗</span>
                </a>
                <div className={styles.cardActions}>
                  <button
                    className={styles.secondaryButton}
                    disabled={!source.manual_upload_eligible}
                    onClick={() => startUpload(source)}
                    title={
                      source.manual_upload_eligible
                        ? "Upload source evidence"
                        : "Source is not approved for manual uploads"
                    }
                    type="button"
                  >
                    Upload document
                  </button>
                  <button
                    className={styles.primaryButton}
                    disabled={
                      !source.automatic_fetch_eligible ||
                      activeAction === `crawl:${source.id}`
                    }
                    onClick={() => void runCrawler(source)}
                    title={
                      source.automatic_fetch_eligible
                        ? "Run the approved crawler"
                        : "Source is not approved for automatic crawling"
                    }
                    type="button"
                  >
                    {activeAction === `crawl:${source.id}`
                      ? "Queuing…"
                      : "Run crawler"}
                  </button>
                </div>
              </article>
            ))}
          </div>
          {!filteredSources.length ? (
            <div className={styles.emptyState}>
              <strong>No matching sources</strong>
              <span>
                Approved sources appear after the reviewed registry is deployed.
              </span>
            </div>
          ) : null}
          <p className={styles.registryNote}>
            Approval, crawl policy, adapter, and schedule remain
            version-controlled in the source registry so the dashboard cannot
            silently expand crawler scope.
          </p>
        </section>

        <section className={styles.section} aria-labelledby="jobs-heading">
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.eyebrow}>Activity</p>
              <h2 id="jobs-heading">Recent ingestion jobs</h2>
            </div>
            <span className={styles.jobCount}>{jobs.length} shown</span>
          </div>
          <div className={styles.tableFrame}>
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Attempt</th>
                  <th>Queued</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <strong>{job.source_title}</strong>
                      <small>{compactId(job.id)}</small>
                    </td>
                    <td>
                      <span
                        className={styles.jobStatus}
                        data-status={job.status}
                      >
                        {job.status.replace("_", " ")}
                      </span>
                    </td>
                    <td>
                      {job.attempt_count} / {job.max_attempts}
                    </td>
                    <td>{formatDate(job.scheduled_at)}</td>
                    <td>
                      {job.error_message ??
                        (job.completed_at
                          ? formatDate(job.completed_at)
                          : "Pending")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!jobs.length ? (
              <div className={styles.emptyState}>
                <strong>No ingestion jobs yet</strong>
                <span>
                  Run an eligible crawler or upload an approved document to
                  begin.
                </span>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}

function Brand() {
  return (
    <Link className={styles.brand} href="/" aria-label="Uzbekistan OS home">
      <span className={styles.brandMark} aria-hidden="true">
        U
      </span>
      <span>
        <strong>Uzbekistan OS</strong>
        <small>Admin operations</small>
      </span>
    </Link>
  );
}

function Stat({
  label,
  value,
  detail,
  attention = false,
}: {
  label: string;
  value: ReactNode;
  detail: string;
  attention?: boolean;
}) {
  return (
    <article className={styles.statCard} data-attention={attention}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
