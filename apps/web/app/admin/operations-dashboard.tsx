"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { ThemeToggle } from "../design-system/theme-toggle";
import styles from "./operations-dashboard.module.css";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
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
    reader.onerror = () => reject(new Error("The selected file could not be read."));
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
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
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
        payload.error?.message ?? `Request failed with status ${response.status}.`,
      );
    }
    return payload.data;
  }

  async function loadOperations(bearerToken: string = token) {
    if (!bearerToken) return;
    setBusy(true);
    setError("");
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
      setToken(bearerToken);
      setPrincipal(identity);
      setSources(nextSources);
      setJobs(nextJobs);
    } catch (caught) {
      setPrincipal(null);
      setSources([]);
      setJobs([]);
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleaned = tokenInput.trim();
    if (!cleaned) return;
    setMessage("");
    void loadOperations(cleaned);
  }

  function disconnect() {
    setToken("");
    setTokenInput("");
    setPrincipal(null);
    setSources([]);
    setJobs([]);
    setUploadSource(null);
    setUploadFile(null);
    setMessage("Administrator session disconnected.");
  }

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
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      setMessage(`Crawler job ${compactId(job.id)} queued for ${source.title}.`);
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
      const nextJobs = await request<IngestionJob[]>("/admin/ingestion/jobs?limit=50");
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

  const stats = useMemo(
    () => ({
      active: sources.filter((source) => source.active).length,
      scheduled: sources.filter((source) => source.schedule_interval_minutes !== null).length,
      review: jobs.filter((job) => job.status === "succeeded").length,
      attention: jobs.filter((job) =>
        ["retry_scheduled", "dead_lettered"].includes(job.status),
      ).length,
    }),
    [jobs, sources],
  );

  if (!principal) {
    return (
      <main className={styles.shell}>
        <header className={styles.topbar}>
          <Brand />
          <ThemeToggle className={styles.themeButton} />
        </header>
        <section className={styles.connectPanel} aria-labelledby="connect-title">
          <p className={styles.eyebrow}>Restricted operations</p>
          <h1 id="connect-title">Manage trusted knowledge sources.</h1>
          <p>
            Connect an administrator access token to upload official documents,
            run approved crawlers, and monitor ingestion health.
          </p>
          <form className={styles.connectForm} onSubmit={connect}>
            <label htmlFor="admin-token">Administrator access token</label>
            <div>
              <input
                autoComplete="off"
                id="admin-token"
                onChange={(event) => setTokenInput(event.target.value)}
                placeholder="Paste a short-lived Bearer token"
                type="password"
                value={tokenInput}
              />
              <button disabled={busy || !tokenInput.trim()} type="submit">
                {busy ? "Connecting…" : "Connect"}
              </button>
            </div>
          </form>
          <p className={styles.securityNote}>
            The token stays in page memory and is cleared when you disconnect or
            close this tab. Source approval is managed in the reviewed registry.
          </p>
          {error ? <p className={styles.error} role="alert">{error}</p> : null}
          {message ? <p className={styles.notice} role="status">{message}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <Brand />
        <nav className={styles.topActions} aria-label="Admin utilities">
          <Link href="/admin/reviews">Review queue</Link>
          <ThemeToggle className={styles.themeButton} />
          <button className={styles.quietButton} onClick={disconnect} type="button">
            Disconnect
          </button>
        </nav>
      </header>

      <div className={styles.page}>
        <section className={styles.hero}>
          <div>
            <p className={styles.eyebrow}>Knowledge operations</p>
            <h1>Ingestion control center</h1>
            <p>
              Curate official evidence, operate allowlisted crawlers, and follow every
              job into the human review queue.
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
          <Stat label="Active sources" value={stats.active} detail={`${sources.length} configured`} />
          <Stat label="Scheduled" value={stats.scheduled} detail="Registry controlled" />
          <Stat label="Processed" value={stats.review} detail="Recent successful jobs" />
          <Stat label="Needs attention" value={stats.attention} detail="Retry or failed" attention={stats.attention > 0} />
        </section>

        <div className={styles.feedback} aria-live="polite">
          {error ? <p className={styles.error} role="alert">{error}</p> : null}
          {message ? <p className={styles.notice} role="status">{message}</p> : null}
        </div>

        {uploadSource ? (
          <section className={styles.uploadPanel} aria-labelledby="upload-heading">
            <div>
              <p className={styles.eyebrow}>Manual evidence</p>
              <h2 id="upload-heading">Upload for {uploadSource.title}</h2>
              <p>
                Accepted: PDF, HTML, XHTML, or plain text. Maximum 10 MB. The file is
                checksum-verified, stored as source evidence, and queued for review.
              </p>
            </div>
            <form onSubmit={uploadEvidence}>
              <label className={styles.filePicker} htmlFor="evidence-file">
                <span>{uploadFile ? uploadFile.name : "Choose official document"}</span>
                <small>{uploadFile ? `${Math.ceil(uploadFile.size / 1024)} KB` : "PDF, HTML, or TXT"}</small>
              </label>
              <input
                accept=".pdf,.html,.htm,.txt,application/pdf,text/html,application/xhtml+xml,text/plain"
                className={styles.visuallyHidden}
                id="evidence-file"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
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
                  disabled={!uploadFile || activeAction === `upload:${uploadSource.id}`}
                  type="submit"
                >
                  {activeAction === `upload:${uploadSource.id}` ? "Processing…" : "Upload and process"}
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
                  <div className={styles.sourceIcon} data-type={source.source_type} aria-hidden="true">
                    {source.source_type === "pdf" ? "PDF" : "WWW"}
                  </div>
                  <div>
                    <div className={styles.pills}>
                      <span data-tone={source.registry_status === "approved" ? "success" : "neutral"}>
                        {source.registry_status}
                      </span>
                      <span>{sourceTypeLabel(source.source_type)}</span>
                    </div>
                    <h3>{source.title}</h3>
                    <p>{source.organization}</p>
                  </div>
                </div>
                <dl className={styles.sourceMeta}>
                  <div><dt>Domains</dt><dd>{source.domains.join(", ")}</dd></div>
                  <div><dt>Languages</dt><dd>{source.languages.map((item) => item.toUpperCase()).join(", ")}</dd></div>
                  <div><dt>Policy</dt><dd>{source.crawl_policy.replace("_", " ")}</dd></div>
                  <div><dt>Verified</dt><dd>{formatDate(source.last_verified_at)}</dd></div>
                </dl>
                <a className={styles.sourceLink} href={source.url} rel="noreferrer" target="_blank">
                  View official source <span aria-hidden="true">↗</span>
                </a>
                <div className={styles.cardActions}>
                  <button
                    className={styles.secondaryButton}
                    disabled={!source.manual_upload_eligible}
                    onClick={() => startUpload(source)}
                    title={source.manual_upload_eligible ? "Upload source evidence" : "Source is not approved for manual uploads"}
                    type="button"
                  >
                    Upload document
                  </button>
                  <button
                    className={styles.primaryButton}
                    disabled={!source.automatic_fetch_eligible || activeAction === `crawl:${source.id}`}
                    onClick={() => void runCrawler(source)}
                    title={source.automatic_fetch_eligible ? "Run the approved crawler" : "Source is not approved for automatic crawling"}
                    type="button"
                  >
                    {activeAction === `crawl:${source.id}` ? "Queuing…" : "Run crawler"}
                  </button>
                </div>
              </article>
            ))}
          </div>
          {!filteredSources.length ? (
            <div className={styles.emptyState}>
              <strong>No matching sources</strong>
              <span>Approved sources appear after the reviewed registry is deployed.</span>
            </div>
          ) : null}
          <p className={styles.registryNote}>
            Approval, crawl policy, adapter, and schedule remain version-controlled in
            the source registry so the dashboard cannot silently expand crawler scope.
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
                <tr><th>Source</th><th>Status</th><th>Attempt</th><th>Queued</th><th>Result</th></tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td><strong>{job.source_title}</strong><small>{compactId(job.id)}</small></td>
                    <td><span className={styles.jobStatus} data-status={job.status}>{job.status.replace("_", " ")}</span></td>
                    <td>{job.attempt_count} / {job.max_attempts}</td>
                    <td>{formatDate(job.scheduled_at)}</td>
                    <td>{job.error_message ?? (job.completed_at ? formatDate(job.completed_at) : "Pending")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!jobs.length ? <div className={styles.emptyState}><strong>No ingestion jobs yet</strong><span>Run an eligible crawler or upload an approved document to begin.</span></div> : null}
          </div>
        </section>
      </div>
    </main>
  );
}

function Brand() {
  return (
    <Link className={styles.brand} href="/" aria-label="Uzbekistan OS home">
      <span className={styles.brandMark} aria-hidden="true">U</span>
      <span><strong>Uzbekistan OS</strong><small>Admin operations</small></span>
    </Link>
  );
}

function Stat({ label, value, detail, attention = false }: { label: string; value: number; detail: string; attention?: boolean }) {
  return (
    <article className={styles.statCard} data-attention={attention}>
      <span>{label}</span><strong>{value}</strong><small>{detail}</small>
    </article>
  );
}
