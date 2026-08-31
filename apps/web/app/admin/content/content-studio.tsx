"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAdminApiSession } from "@/lib/admin-api-session";
import { ThemeToggle } from "../../design-system/theme-toggle";
import styles from "./content-studio.module.css";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const statusFilters = [
  "all",
  "draft",
  "in_review",
  "approved",
  "published",
] as const;
const domainOptions = [
  ["immigration", "Immigration"],
  ["tourism", "Tourism"],
  ["business-registration", "Business registration"],
  ["healthcare", "Healthcare"],
  ["everyday-living", "Everyday living"],
] as const;
const languageOptions = [
  ["uz", "Uzbek"],
  ["en", "English"],
  ["ru", "Russian"],
] as const;

type EditorialStatus =
  "draft" | "in_review" | "approved" | "published" | "stale" | "archived";
type ContentType = "article" | "guide" | "platform_update" | "interview";
type Principal = { id: string; roles: string[] };
type Author = {
  id: string;
  principal_id: string | null;
  slug: string;
  name: string;
  bio: string | null;
  avatar_url: string | null;
  profile_url: string | null;
  is_active: boolean;
};
type Source = {
  id: string;
  title: string;
  organization: string;
  url: string;
  active: boolean;
  registry_status: string;
};
type PostSummary = {
  id: string;
  slug: string;
  content_type: ContentType;
  domain_slug: string | null;
  language_code: string;
  status: EditorialStatus;
  published_version_id: string | null;
  latest_revision_id: string;
  latest_revision_number: number;
  latest_revision_status: EditorialStatus;
  latest_title: string;
  updated_at: string;
};
type Revision = {
  id: string;
  post_id: string;
  version_number: number;
  content_type: ContentType;
  status: EditorialStatus;
  submitted_at: string | null;
  reviewed_at: string | null;
  decision_reason: string | null;
  published_at: string | null;
  include_in_rag: boolean;
};
type Citation = {
  source_id: string;
  document_version_id: string | null;
  locator: string;
  quote: string | null;
};
type RevisionDetail = {
  revision: Revision;
  slug: string;
  domain_slug: string | null;
  language_code: string;
  title: string;
  summary: string;
  body_markdown: string;
  structured_content: Record<string, unknown>;
  seo_title: string | null;
  seo_description: string | null;
  canonical_url: string | null;
  hero_image_url: string | null;
  hero_image_alt: string | null;
  include_in_rag: boolean;
  author: Author;
  sources: Citation[];
};
type Envelope<T> = { data: T; meta: { request_id: string } };
type ErrorEnvelope = { error?: { code?: string; message?: string } };

type EditorDraft = {
  authorId: string;
  bodyMarkdown: string;
  canonicalUrl: string;
  citations: Citation[];
  contentType: ContentType;
  domainSlug: string;
  heroImageAlt: string;
  heroImageUrl: string;
  includeInRag: boolean;
  languageCode: string;
  seoDescription: string;
  seoTitle: string;
  slug: string;
  structuredJson: string;
  summary: string;
  title: string;
};

function emptyDraft(authorId = ""): EditorDraft {
  return {
    authorId,
    bodyMarkdown: "",
    canonicalUrl: "",
    citations: [],
    contentType: "article",
    domainSlug: "tourism",
    heroImageAlt: "",
    heroImageUrl: "",
    includeInRag: false,
    languageCode: "en",
    seoDescription: "",
    seoTitle: "",
    slug: "",
    structuredJson: "{}",
    summary: "",
    title: "",
  };
}

function draftFromDetail(detail: RevisionDetail): EditorDraft {
  return {
    authorId: detail.author.id,
    bodyMarkdown: detail.body_markdown,
    canonicalUrl: detail.canonical_url ?? "",
    citations: detail.sources,
    contentType: detail.revision.content_type,
    domainSlug: detail.domain_slug ?? "",
    heroImageAlt: detail.hero_image_alt ?? "",
    heroImageUrl: detail.hero_image_url ?? "",
    includeInRag: detail.include_in_rag,
    languageCode: detail.language_code,
    seoDescription: detail.seo_description ?? "",
    seoTitle: detail.seo_title ?? "",
    slug: detail.slug,
    structuredJson: JSON.stringify(detail.structured_content, null, 2),
    summary: detail.summary,
    title: detail.title,
  };
}

function slugify(value: string) {
  return value
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 100);
}

function formatStatus(status: EditorialStatus) {
  return status.replace("_", " ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function messageFrom(error: unknown) {
  return error instanceof Error
    ? error.message
    : "The editorial service could not complete this request.";
}

export default function ContentStudio() {
  const adminSession = useAdminApiSession();
  const token = adminSession.accessToken ?? "";
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [posts, setPosts] = useState<PostSummary[]>([]);
  const [filter, setFilter] = useState<(typeof statusFilters)[number]>("all");
  const [selectedPost, setSelectedPost] = useState<PostSummary | null>(null);
  const [detail, setDetail] = useState<RevisionDetail | null>(null);
  const [draft, setDraft] = useState<EditorDraft>(emptyDraft());
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [action, setAction] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [authorBio, setAuthorBio] = useState("");

  const ownAuthor = useMemo(
    () =>
      authors.find((author) => author.principal_id === principal?.id) ?? null,
    [authors, principal?.id],
  );
  const editable = creating || detail?.revision.status === "draft";
  const eligibleSources = useMemo(
    () =>
      sources.filter(
        (source) => source.active && source.registry_status === "approved",
      ),
    [sources],
  );

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
          `Editorial request failed with status ${response.status}.`,
      );
    }
    return payload.data;
  }

  async function loadWorkspace(bearerToken = token) {
    if (!bearerToken) return;
    setLoading(true);
    setError("");
    try {
      const [nextPrincipal, nextAuthors, nextPosts, nextSources] =
        await Promise.all([
          request<Principal>("/auth/me", undefined, bearerToken),
          request<Author[]>("/admin/content/authors", undefined, bearerToken),
          request<PostSummary[]>(
            "/admin/content/posts?limit=100",
            undefined,
            bearerToken,
          ),
          request<Source[]>("/admin/sources", undefined, bearerToken),
        ]);
      if (!nextPrincipal.roles.includes("admin")) {
        throw new Error(
          "The editorial studio requires the administrator role.",
        );
      }
      setPrincipal(nextPrincipal);
      setAuthors(nextAuthors);
      setPosts(nextPosts);
      setSources(nextSources);
      if (!selectedPost && nextPosts.length > 0) {
        await selectPost(nextPosts[0], bearerToken);
      }
    } catch (nextError) {
      setError(messageFrom(nextError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (adminSession.loading || !adminSession.accessToken) return;
    void Promise.resolve().then(() =>
      loadWorkspace(adminSession.accessToken ?? ""),
    );
    // The access token is the only session value that should trigger a reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminSession.accessToken, adminSession.loading]);

  async function selectPost(post: PostSummary, bearerToken: string = token) {
    setSelectedPost(post);
    setCreating(false);
    setDetail(null);
    setDetailLoading(true);
    setError("");
    setNotice("");
    try {
      const nextDetail = await request<RevisionDetail>(
        `/admin/content/revisions/${post.latest_revision_id}`,
        undefined,
        bearerToken,
      );
      setDetail(nextDetail);
      setDraft(draftFromDetail(nextDetail));
      setDecisionReason(nextDetail.revision.decision_reason ?? "");
    } catch (nextError) {
      setError(messageFrom(nextError));
    } finally {
      setDetailLoading(false);
    }
  }

  function startNewPost() {
    setCreating(true);
    setSelectedPost(null);
    setDetail(null);
    setDraft(emptyDraft(ownAuthor?.id ?? authors[0]?.id ?? ""));
    setDecisionReason("");
    setError("");
    setNotice("");
  }

  function updateDraft<K extends keyof EditorDraft>(
    field: K,
    value: EditorDraft[K],
  ) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function addCitation() {
    updateDraft("citations", [
      ...draft.citations,
      {
        source_id: eligibleSources[0]?.id ?? "",
        document_version_id: null,
        locator: "",
        quote: null,
      },
    ]);
  }

  function updateCitation(index: number, patch: Partial<Citation>) {
    updateDraft(
      "citations",
      draft.citations.map((citation, citationIndex) =>
        citationIndex === index ? { ...citation, ...patch } : citation,
      ),
    );
  }

  function removeCitation(index: number) {
    updateDraft(
      "citations",
      draft.citations.filter((_, citationIndex) => citationIndex !== index),
    );
  }

  function revisionPayload() {
    let structuredContent: Record<string, unknown>;
    try {
      const parsed = JSON.parse(draft.structuredJson) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error();
      }
      structuredContent = parsed as Record<string, unknown>;
    } catch {
      throw new Error("Structured data must be a valid JSON object.");
    }
    if (!draft.authorId) throw new Error("Choose an author before saving.");
    if (draft.contentType === "guide" && draft.citations.length === 0) {
      throw new Error("Guides require at least one approved official source.");
    }
    if (
      draft.includeInRag &&
      (!draft.domainSlug || draft.citations.length === 0)
    ) {
      throw new Error(
        "Assistant retrieval requires a topic and at least one approved official source.",
      );
    }
    if (
      draft.citations.some(
        (citation) => !citation.source_id || !citation.locator.trim(),
      )
    ) {
      throw new Error("Every source needs a source selection and locator.");
    }
    return {
      author_id: draft.authorId,
      title: draft.title.trim(),
      summary: draft.summary.trim(),
      body_markdown: draft.bodyMarkdown.trim(),
      structured_content: structuredContent,
      seo_title: draft.seoTitle.trim() || null,
      seo_description: draft.seoDescription.trim() || null,
      canonical_url: draft.canonicalUrl.trim() || null,
      hero_image_url: draft.heroImageUrl.trim() || null,
      hero_image_alt: draft.heroImageAlt.trim() || null,
      include_in_rag: draft.includeInRag,
      sources: draft.citations.map((citation) => ({
        ...citation,
        locator: citation.locator.trim(),
        quote: citation.quote?.trim() || null,
      })),
    };
  }

  async function saveDraft(event?: FormEvent): Promise<boolean> {
    event?.preventDefault();
    setAction("save");
    setError("");
    setNotice("");
    try {
      const payload = revisionPayload();
      let revision: Revision;
      if (creating) {
        revision = await request<Revision>("/admin/content/posts", {
          method: "POST",
          body: JSON.stringify({
            ...payload,
            slug: draft.slug,
            content_type: draft.contentType,
            domain_slug: draft.domainSlug || null,
            language_code: draft.languageCode,
          }),
        });
      } else if (detail) {
        const nextDetail = await request<RevisionDetail>(
          `/admin/content/revisions/${detail.revision.id}`,
          { method: "PUT", body: JSON.stringify(payload) },
        );
        revision = nextDetail.revision;
        setDetail(nextDetail);
      } else {
        throw new Error("Choose a post before saving.");
      }
      const nextPosts = await request<PostSummary[]>(
        "/admin/content/posts?limit=100",
      );
      setPosts(nextPosts);
      const post = nextPosts.find(
        (item) => item.latest_revision_id === revision.id,
      );
      if (post) await selectPost(post);
      setNotice("Draft saved with a new audit event.");
      return true;
    } catch (nextError) {
      setError(messageFrom(nextError));
      return false;
    } finally {
      setAction(null);
    }
  }

  async function transition(
    nextAction: "submit" | "approve" | "request_changes" | "publish",
  ) {
    if (!detail) return;
    setAction(nextAction);
    setError("");
    setNotice("");
    try {
      if (nextAction === "submit") {
        const saved = await saveDraft();
        if (!saved) return;
        setAction("submit");
        await request<Revision>(
          `/admin/content/revisions/${detail.revision.id}/submit`,
          { method: "POST" },
        );
      } else if (nextAction === "publish") {
        await request<Revision>(
          `/admin/content/revisions/${detail.revision.id}/publish`,
          { method: "POST" },
        );
      } else {
        if (!decisionReason.trim()) {
          throw new Error("Add an internal review reason before deciding.");
        }
        await request<Revision>(
          `/admin/content/revisions/${detail.revision.id}/decision`,
          {
            method: "POST",
            body: JSON.stringify({
              decision: nextAction,
              reason: decisionReason.trim(),
            }),
          },
        );
      }
      const nextPosts = await request<PostSummary[]>(
        "/admin/content/posts?limit=100",
      );
      setPosts(nextPosts);
      const post = nextPosts.find(
        (item) => item.id === detail.revision.post_id,
      );
      if (post) await selectPost(post);
      setNotice(
        nextAction === "publish"
          ? "Post published successfully."
          : "Editorial workflow updated.",
      );
    } catch (nextError) {
      setError(messageFrom(nextError));
    } finally {
      setAction(null);
    }
  }

  async function createNextRevision() {
    if (!detail || !selectedPost) return;
    setAction("revision");
    setError("");
    try {
      const revision = await request<Revision>(
        `/admin/content/posts/${selectedPost.id}/revisions`,
        { method: "POST", body: JSON.stringify(revisionPayload()) },
      );
      const nextPosts = await request<PostSummary[]>(
        "/admin/content/posts?limit=100",
      );
      setPosts(nextPosts);
      const post = nextPosts.find(
        (item) => item.latest_revision_id === revision.id,
      );
      if (post) await selectPost(post);
      setNotice("A new draft revision is ready to edit.");
    } catch (nextError) {
      setError(messageFrom(nextError));
    } finally {
      setAction(null);
    }
  }

  async function createAuthor(event: FormEvent) {
    event.preventDefault();
    setAction("author");
    setError("");
    try {
      const author = await request<Author>("/admin/content/authors", {
        method: "POST",
        body: JSON.stringify({
          slug: slugify(authorName),
          name: authorName.trim(),
          bio: authorBio.trim() || null,
          avatar_url: null,
          profile_url: null,
        }),
      });
      setAuthors((current) => [...current, author]);
      setDraft((current) => ({ ...current, authorId: author.id }));
      setNotice("Your author profile is ready.");
    } catch (nextError) {
      setError(messageFrom(nextError));
    } finally {
      setAction(null);
    }
  }

  const visiblePosts = posts.filter(
    (post) => filter === "all" || post.latest_revision_status === filter,
  );
  const connectionError =
    error ||
    (!adminSession.loading && !adminSession.accessToken
      ? (adminSession.error ?? "Administrator authentication is required.")
      : "");

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <Link className={styles.brand} href="/" aria-label="Uzbekistan OS home">
          <span className={styles.brandMark} aria-hidden="true">
            U
          </span>
          <span>
            <strong>Uzbekistan OS</strong>
            <small>Editorial operations</small>
          </span>
        </Link>
        <nav className={styles.topnav} aria-label="Admin workspaces">
          <Link href="/admin">Ingestion</Link>
          <Link href="/admin/reviews">Evidence review</Link>
          <Link className={styles.activeNav} href="/admin/content">
            Content
          </Link>
          <Link href="/admin/feedback">Feedback</Link>
          <ThemeToggle className={styles.themeButton} />
          <Link className={styles.accountButton} href="/account">
            Account
          </Link>
        </nav>
      </header>

      {loading || adminSession.loading ? (
        <section className={styles.connectPanel} aria-live="polite">
          <span className={styles.loader} aria-hidden="true" />
          <h1>Opening the editorial studio</h1>
          <p>Verifying your staff role and loading the content library.</p>
        </section>
      ) : connectionError && !principal ? (
        <section className={styles.connectPanel}>
          <h1>Editorial studio unavailable</h1>
          <p role="alert">{connectionError}</p>
          <Link className={styles.primaryButton} href="/account">
            Return to account
          </Link>
        </section>
      ) : (
        <div className={styles.workspace}>
          <aside className={styles.library}>
            <div className={styles.libraryHeader}>
              <div>
                <p className={styles.eyebrow}>Content library</p>
                <h1>Articles & guides</h1>
              </div>
              <button
                className={styles.newButton}
                onClick={startNewPost}
                type="button"
              >
                + New
              </button>
            </div>
            <div
              className={styles.filters}
              aria-label="Filter content by status"
            >
              {statusFilters.map((status) => (
                <button
                  aria-pressed={filter === status}
                  className={filter === status ? styles.filterActive : ""}
                  key={status}
                  onClick={() => setFilter(status)}
                  type="button"
                >
                  {status === "all" ? "All" : formatStatus(status)}
                </button>
              ))}
            </div>
            <div className={styles.postList}>
              {visiblePosts.map((post) => (
                <button
                  className={
                    selectedPost?.id === post.id && !creating
                      ? styles.postActive
                      : styles.postCard
                  }
                  key={post.id}
                  onClick={() => void selectPost(post)}
                  type="button"
                >
                  <span className={styles.postMeta}>
                    <span data-status={post.latest_revision_status}>
                      {formatStatus(post.latest_revision_status)}
                    </span>
                    <span>v{post.latest_revision_number}</span>
                  </span>
                  <strong>{post.latest_title}</strong>
                  <small>
                    {post.domain_slug?.replace("-", " ") ?? "Company"} ·{" "}
                    {post.language_code.toUpperCase()}
                  </small>
                  <time dateTime={post.updated_at}>
                    {formatDate(post.updated_at)}
                  </time>
                </button>
              ))}
              {visiblePosts.length === 0 ? (
                <div className={styles.emptyList}>
                  <strong>No posts in this view</strong>
                  <p>Create a post or choose another status.</p>
                </div>
              ) : null}
            </div>
          </aside>

          <section className={styles.editor}>
            {!ownAuthor ? (
              <form className={styles.authorSetup} onSubmit={createAuthor}>
                <div>
                  <p className={styles.eyebrow}>One-time setup</p>
                  <h2>Create your author profile</h2>
                  <p>
                    Every published post identifies the responsible human
                    author. This profile is attached to the audit trail.
                  </p>
                </div>
                <label>
                  Display name
                  <input
                    onChange={(event) => setAuthorName(event.target.value)}
                    required
                    value={authorName}
                  />
                </label>
                <label>
                  Short bio
                  <textarea
                    onChange={(event) => setAuthorBio(event.target.value)}
                    rows={3}
                    value={authorBio}
                  />
                </label>
                <button
                  className={styles.primaryButton}
                  disabled={action === "author"}
                  type="submit"
                >
                  {action === "author" ? "Creating…" : "Create author profile"}
                </button>
              </form>
            ) : creating || detail ? (
              <form className={styles.editorForm} onSubmit={saveDraft}>
                <div className={styles.editorHeading}>
                  <div>
                    <p className={styles.eyebrow}>
                      {creating
                        ? "New editorial draft"
                        : `${formatStatus(detail?.revision.status ?? "draft")} · Version ${detail?.revision.version_number}`}
                    </p>
                    <h2>{creating ? "Create a new post" : draft.title}</h2>
                    <p>
                      Drafts are private. Only approved revisions can be
                      published to the public blog.
                    </p>
                  </div>
                  <div className={styles.headingActions}>
                    {!creating && detail?.revision.status === "published" ? (
                      <button
                        className={styles.secondaryButton}
                        disabled={Boolean(action)}
                        onClick={() => void createNextRevision()}
                        type="button"
                      >
                        Create revision
                      </button>
                    ) : null}
                    {editable ? (
                      <button
                        className={styles.primaryButton}
                        disabled={Boolean(action)}
                        type="submit"
                      >
                        {action === "save" ? "Saving…" : "Save draft"}
                      </button>
                    ) : null}
                  </div>
                </div>

                {error ? (
                  <p className={styles.error} role="alert">
                    {error}
                  </p>
                ) : null}
                {notice ? (
                  <p className={styles.notice} role="status">
                    {notice}
                  </p>
                ) : null}

                {creating ? (
                  <fieldset className={styles.identityFields}>
                    <legend>Post identity</legend>
                    <label>
                      URL slug
                      <input
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("slug", event.target.value)
                        }
                        pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
                        placeholder="best-time-to-visit-uzbekistan"
                        required
                        value={draft.slug}
                      />
                    </label>
                    <label>
                      Content type
                      <select
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft(
                            "contentType",
                            event.target.value as ContentType,
                          )
                        }
                        value={draft.contentType}
                      >
                        <option value="article">Article</option>
                        <option value="guide">Official guide</option>
                        <option value="interview">Interview</option>
                        <option value="platform_update">Platform update</option>
                      </select>
                    </label>
                    <label>
                      Topic
                      <select
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("domainSlug", event.target.value)
                        }
                        value={draft.domainSlug}
                      >
                        {domainOptions.map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Language
                      <select
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("languageCode", event.target.value)
                        }
                        value={draft.languageCode}
                      >
                        {languageOptions.map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </fieldset>
                ) : null}

                <div className={styles.formGrid}>
                  <section className={styles.primaryFields}>
                    <label>
                      Title
                      <input
                        disabled={!editable}
                        maxLength={500}
                        onChange={(event) => {
                          updateDraft("title", event.target.value);
                          if (creating && !draft.slug) {
                            updateDraft("slug", slugify(event.target.value));
                          }
                        }}
                        required
                        value={draft.title}
                      />
                    </label>
                    <label>
                      Summary
                      <textarea
                        disabled={!editable}
                        maxLength={2000}
                        onChange={(event) =>
                          updateDraft("summary", event.target.value)
                        }
                        required
                        rows={4}
                        value={draft.summary}
                      />
                      <span className={styles.counter}>
                        {draft.summary.length}/2,000
                      </span>
                    </label>
                    <label>
                      Article body · Markdown
                      <textarea
                        className={styles.markdown}
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("bodyMarkdown", event.target.value)
                        }
                        required
                        rows={24}
                        spellCheck
                        value={draft.bodyMarkdown}
                      />
                    </label>
                  </section>

                  <aside className={styles.metadataPanel}>
                    <div className={styles.panelHeading}>
                      <p className={styles.eyebrow}>Search & discovery</p>
                      <h3>SEO metadata</h3>
                    </div>
                    <label>
                      SEO title
                      <input
                        disabled={!editable}
                        maxLength={70}
                        onChange={(event) =>
                          updateDraft("seoTitle", event.target.value)
                        }
                        value={draft.seoTitle}
                      />
                      <span className={styles.counter}>
                        {draft.seoTitle.length}/70
                      </span>
                    </label>
                    <label>
                      Meta description
                      <textarea
                        disabled={!editable}
                        maxLength={200}
                        onChange={(event) =>
                          updateDraft("seoDescription", event.target.value)
                        }
                        rows={4}
                        value={draft.seoDescription}
                      />
                      <span className={styles.counter}>
                        {draft.seoDescription.length}/200
                      </span>
                    </label>
                    <label>
                      Canonical URL
                      <input
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("canonicalUrl", event.target.value)
                        }
                        placeholder="https://www.uzbekistanos.com/blog/..."
                        type="url"
                        value={draft.canonicalUrl}
                      />
                    </label>
                    <label>
                      Hero image URL
                      <input
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("heroImageUrl", event.target.value)
                        }
                        type="url"
                        value={draft.heroImageUrl}
                      />
                    </label>
                    <label>
                      Hero image alt text
                      <input
                        disabled={!editable}
                        maxLength={500}
                        onChange={(event) =>
                          updateDraft("heroImageAlt", event.target.value)
                        }
                        value={draft.heroImageAlt}
                      />
                    </label>
                    <label>
                      Author
                      <select
                        disabled={!editable}
                        onChange={(event) =>
                          updateDraft("authorId", event.target.value)
                        }
                        required
                        value={draft.authorId}
                      >
                        <option value="">Choose author</option>
                        {authors.map((author) => (
                          <option key={author.id} value={author.id}>
                            {author.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className={styles.ragControl}>
                      <label>
                        <input
                          checked={draft.includeInRag}
                          disabled={!editable}
                          onChange={(event) =>
                            updateDraft("includeInRag", event.target.checked)
                          }
                          type="checkbox"
                        />
                        <span>
                          <strong>Include in assistant retrieval (RAG)</strong>
                          <small>
                            Default is excluded. Included revisions become
                            retrievable only after review and publication, and
                            require a topic plus verified official citations.
                          </small>
                        </span>
                      </label>
                      <p>
                        Manual reviewed corrections remain higher priority than
                        editorial posts when official websites are outdated.
                      </p>
                    </div>
                  </aside>
                </div>

                <section className={styles.citationsPanel}>
                  <div className={styles.sectionHeading}>
                    <div>
                      <p className={styles.eyebrow}>Trust layer</p>
                      <h3>Official sources</h3>
                      <p>
                        Cite factual claims precisely. Guides cannot enter
                        review without an active official source.
                      </p>
                    </div>
                    {editable ? (
                      <button
                        className={styles.secondaryButton}
                        onClick={addCitation}
                        type="button"
                      >
                        + Add source
                      </button>
                    ) : null}
                  </div>
                  <div className={styles.citationList}>
                    {draft.citations.map((citation, index) => (
                      <div
                        className={styles.citationCard}
                        key={`${index}-${citation.source_id}`}
                      >
                        <label>
                          Approved source
                          <select
                            disabled={!editable}
                            onChange={(event) =>
                              updateCitation(index, {
                                source_id: event.target.value,
                              })
                            }
                            required
                            value={citation.source_id}
                          >
                            <option value="">Choose source</option>
                            {eligibleSources.map((source) => (
                              <option key={source.id} value={source.id}>
                                {source.organization} · {source.title}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Locator
                          <input
                            disabled={!editable}
                            onChange={(event) =>
                              updateCitation(index, {
                                locator: event.target.value,
                              })
                            }
                            placeholder="Article 12, Fees section, or page 4"
                            required
                            value={citation.locator}
                          />
                        </label>
                        <label className={styles.quoteField}>
                          Supporting quote or note
                          <textarea
                            disabled={!editable}
                            onChange={(event) =>
                              updateCitation(index, {
                                quote: event.target.value,
                              })
                            }
                            rows={2}
                            value={citation.quote ?? ""}
                          />
                        </label>
                        {editable ? (
                          <button
                            className={styles.removeButton}
                            onClick={() => removeCitation(index)}
                            type="button"
                          >
                            Remove
                          </button>
                        ) : null}
                      </div>
                    ))}
                    {draft.citations.length === 0 ? (
                      <p className={styles.emptyCitations}>
                        No sources added yet.
                      </p>
                    ) : null}
                  </div>
                </section>

                <details className={styles.structuredPanel}>
                  <summary>
                    Structured data for search and LLM extraction
                  </summary>
                  <p>
                    Optional JSON for FAQs, key takeaways, entities, or other
                    machine-readable content. It must be a JSON object.
                  </p>
                  <textarea
                    disabled={!editable}
                    onChange={(event) =>
                      updateDraft("structuredJson", event.target.value)
                    }
                    rows={12}
                    spellCheck={false}
                    value={draft.structuredJson}
                  />
                </details>

                {!creating && detail ? (
                  <section className={styles.workflowPanel}>
                    <div>
                      <p className={styles.eyebrow}>Editorial workflow</p>
                      <h3>Review and publication</h3>
                      <p>
                        Every transition is role-checked and written to the
                        immutable administrative audit log.
                      </p>
                    </div>
                    {detail.revision.status === "draft" ? (
                      <button
                        className={styles.primaryButton}
                        disabled={Boolean(action)}
                        onClick={() => void transition("submit")}
                        type="button"
                      >
                        {action === "submit"
                          ? "Submitting…"
                          : "Save and submit for review"}
                      </button>
                    ) : null}
                    {detail.revision.status === "in_review" ? (
                      <div className={styles.decisionControls}>
                        <label>
                          Internal review reason
                          <textarea
                            maxLength={2000}
                            onChange={(event) =>
                              setDecisionReason(event.target.value)
                            }
                            required
                            rows={3}
                            value={decisionReason}
                          />
                        </label>
                        <div>
                          <button
                            className={styles.secondaryButton}
                            disabled={Boolean(action)}
                            onClick={() => void transition("request_changes")}
                            type="button"
                          >
                            Request changes
                          </button>
                          <button
                            className={styles.primaryButton}
                            disabled={Boolean(action)}
                            onClick={() => void transition("approve")}
                            type="button"
                          >
                            Approve revision
                          </button>
                        </div>
                      </div>
                    ) : null}
                    {detail.revision.status === "approved" ? (
                      <button
                        className={styles.publishButton}
                        disabled={Boolean(action)}
                        onClick={() => void transition("publish")}
                        type="button"
                      >
                        {action === "publish" ? "Publishing…" : "Publish post"}
                      </button>
                    ) : null}
                    {detail.revision.status === "published" ? (
                      <div className={styles.publishedState}>
                        <strong>Published</strong>
                        <span>
                          {detail.revision.published_at
                            ? formatDate(detail.revision.published_at)
                            : "Publication recorded"}
                        </span>
                      </div>
                    ) : null}
                  </section>
                ) : null}
              </form>
            ) : detailLoading ? (
              <div className={styles.blankState}>Loading revision…</div>
            ) : (
              <div className={styles.blankState}>
                <span aria-hidden="true">✦</span>
                <h2>Choose a post or create a new one</h2>
                <p>
                  Draft long-form Uzbekistan content, attach official evidence,
                  and move it through review without leaving this workspace.
                </p>
                <button
                  className={styles.primaryButton}
                  onClick={startNewPost}
                  type="button"
                >
                  Create first post
                </button>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
