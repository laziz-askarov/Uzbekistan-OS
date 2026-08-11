"use client";

import Image from "next/image";
import Link from "next/link";
import { MessageResponse } from "@/components/ai-elements/message";
import { createClient } from "@/lib/supabase/client";
import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useMemo,
  useState,
} from "react";
import styles from "./chat-workspace.module.css";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  answer?: VisaApiAnswer;
  workflow?: { id: string; title: string; description: string };
  sources?: VisaApiSource[];
  generated?: boolean;
};

type Chat = { id: string; title: string; messages: Message[] };

type VisaApiAnswer = {
  status: "answered" | "needs_information" | "insufficient";
  summary: string;
  summaryCitationIds: string[];
  sections: { heading: string; content: string; citationIds: string[] }[];
  profile: { field: string; value: string }[];
  missingProfileFields: string[];
  followUpQuestions: string[];
};

type VisaApiSource = {
  id: string;
  title: string;
  url: string;
  reviewedAt: string;
  content: string;
  sourceFile?: string;
};

type VisaApiResult = {
  answer: VisaApiAnswer;
  workflow: { id: string; title: string; description: string };
  sources: VisaApiSource[];
  generated: boolean;
};

const suggestions = [
  ["✈", "Which visa do I need for tourism?"],
  ["⌁", "Check the electronic visa route"],
  ["▣", "What documents should I prepare?"],
  ["◷", "How long does an e-visa take?"],
  ["$", "What are the official visa fees?"],
  ["✓", "What happens after I arrive?"],
] as const;

function newLocalChat(): Chat {
  return { id: crypto.randomUUID(), title: "New conversation", messages: [] };
}

const completedSectionOrder = [
  "route",
  "fees",
  "requirements",
  "documents",
  "application",
  "processing",
  "validity",
  "arrival",
  "registration",
  "restrictions",
] as const;

const sectionVisuals = [
  ["route", "↗"],
  ["fee", "$"],
  ["requirement", "✓"],
  ["document", "▤"],
  ["application", "1"],
  ["process", "◷"],
  ["valid", "◫"],
  ["arrival", "⌁"],
  ["registration", "◎"],
  ["restriction", "!"],
] as const;

function sectionVisual(heading: string) {
  const normalizedHeading = heading.toLocaleLowerCase();
  return (
    sectionVisuals.find(([keyword]) =>
      normalizedHeading.includes(keyword),
    )?.[1] ?? "·"
  );
}

function orderedAnswerSections(answer: VisaApiAnswer) {
  const rank = (heading: string) => {
    const normalizedHeading = heading.toLocaleLowerCase();
    const index = completedSectionOrder.findIndex((keyword) =>
      normalizedHeading.includes(keyword),
    );
    return index === -1 ? completedSectionOrder.length : index;
  };

  return answer.sections
    .map((section, originalIndex) => ({ section, originalIndex }))
    .sort(
      (left, right) =>
        rank(left.section.heading) - rank(right.section.heading) ||
        left.originalIndex - right.originalIndex,
    )
    .map(({ section }) => section);
}

function Icon({
  name,
  size = 16,
}: {
  name: "shield" | "panel" | "plus" | "send" | "arrow" | "external";
  size?: number;
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "shield")
    return (
      <svg {...common}>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      </svg>
    );
  if (name === "panel")
    return (
      <svg {...common}>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M9 3v18" />
      </svg>
    );
  if (name === "plus")
    return (
      <svg {...common}>
        <path d="M12 5v14M5 12h14" />
      </svg>
    );
  if (name === "send")
    return (
      <svg {...common}>
        <path d="m22 2-7 20-4-9-9-4Z" />
        <path d="M22 2 11 13" />
      </svg>
    );
  if (name === "external")
    return (
      <svg {...common}>
        <path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function GeneratedAnswerCard({ message }: { message: Message }) {
  const answer = message.answer;
  if (!answer) return null;
  const orderedSections = orderedAnswerSections(answer);
  const profileTotal =
    answer.profile.length + answer.missingProfileFields.length;
  const progress =
    profileTotal === 0 ? 0 : (answer.profile.length / profileTotal) * 100;
  const sourcesById = new Map(
    message.sources?.map((source) => [source.id, source]),
  );
  const citedIds = new Set([
    ...answer.summaryCitationIds,
    ...answer.sections.flatMap((section) => section.citationIds),
  ]);
  const citedSourceChunks =
    citedIds.size > 0
      ? [...citedIds]
          .map((id) => sourcesById.get(id))
          .filter((source): source is VisaApiSource => Boolean(source))
      : answer.status === "insufficient"
        ? (message.sources ?? []).slice(0, 3)
        : [];
  const citedSources = [
    ...new Map(
      citedSourceChunks.map((source) => [
        source.sourceFile ?? `${source.title}|${source.url}`,
        source,
      ]),
    ).values(),
  ];

  if (answer.status === "needs_information") {
    return (
      <aside className={styles.intakeCard} aria-label="Visa profile progress">
        <div className={styles.intakeHeader}>
          <div>
            <span>Building your visa profile</span>
            <strong>{message.workflow?.title ?? "Visa route"}</strong>
          </div>
          <b>
            {answer.profile.length} of {profileTotal}
          </b>
        </div>
        <div className={styles.progressTrack} aria-hidden="true">
          <span style={{ width: `${progress}%` }} />
        </div>
        {answer.profile.length > 0 ? (
          <dl className={styles.profileFacts}>
            {answer.profile.map((item) => (
              <div key={item.field}>
                <dt>{item.field}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className={styles.intakeHint}>
            We’ll take this one detail at a time.
          </p>
        )}
      </aside>
    );
  }

  return (
    <div
      className={styles.generatedAnswer}
      aria-label={
        answer.status === "answered"
          ? "Completed visa guidance"
          : "Visa guidance status"
      }
    >
      <p className={styles.srOnly}>{answer.summary}</p>
      <div className={styles.workflowBanner}>
        <span>{message.generated ? "Workflow ready" : "Safe fallback"}</span>
        <div>
          <strong>{message.workflow?.title ?? "Visa guidance"}</strong>
          <p>{message.workflow?.description}</p>
        </div>
      </div>
      <section
        className={styles.answerSummary}
        aria-label="Visa guidance summary"
      >
        <span aria-hidden="true">⌖</span>
        <div>
          <strong>What this means for you</strong>
          <p>{answer.summary}</p>
          <div
            className={styles.summaryCitations}
            aria-label="Sources for guidance summary"
          >
            {[...new Set(answer.summaryCitationIds)].map(
              (citationId, index) => {
                const source = sourcesById.get(citationId);
                return source ? (
                  <a
                    href={source.url}
                    key={citationId}
                    target="_blank"
                    rel="noreferrer"
                  >
                    [{index + 1}] {source.title}
                  </a>
                ) : null;
              },
            )}
          </div>
        </div>
      </section>
      {answer.profile.length > 0 ? (
        <section
          className={styles.profileSummary}
          aria-label="Details used for this visa plan"
        >
          <h3>Your details</h3>
          <dl className={styles.profileFacts}>
            {answer.profile.map((item) => (
              <div key={item.field}>
                <dt>{item.field}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
      {orderedSections.map((section) => (
        <details className={styles.generatedSection} key={section.heading} open>
          <summary>
            <span className={styles.sectionHeading}>
              <span aria-hidden="true">{sectionVisual(section.heading)}</span>
              <strong>{section.heading}</strong>
            </span>
            <span className={styles.sectionChevron} aria-hidden="true">
              ⌃
            </span>
          </summary>
          <div className={styles.generatedSectionBody}>
            <MessageResponse>{section.content}</MessageResponse>
            <div
              className={styles.sectionCitations}
              aria-label={`Sources for ${section.heading}`}
            >
              {[...new Set(section.citationIds)].map((citationId, index) => {
                const source = sourcesById.get(citationId);
                return source ? (
                  <a
                    href={source.url}
                    key={citationId}
                    target="_blank"
                    rel="noreferrer"
                  >
                    [{index + 1}] {source.title}
                  </a>
                ) : null;
              })}
            </div>
          </div>
        </details>
      ))}
      {citedSources.length > 0 ? (
        <section className={styles.generatedSources}>
          <h3>Reviewed official sources</h3>
          {citedSources.map((source) => (
            <a
              href={source.url}
              key={source.id}
              target="_blank"
              rel="noreferrer"
            >
              <span>
                <strong>{source.title}</strong>
                <small>
                  {source.sourceFile ? `${source.sourceFile} · ` : ""}Reviewed{" "}
                  {source.reviewedAt}
                </small>
              </span>
              <Icon name="external" size={13} />
            </a>
          ))}
        </section>
      ) : null}
    </div>
  );
}

export default function ChatWorkspace() {
  const supabase = useMemo(() => createClient(), []);
  const [chats, setChats] = useState<Chat[]>(() => [newLocalChat()]);
  const [activeId, setActiveId] = useState(() => chats[0].id);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [account, setAccount] = useState<{
    id: string;
    label: string;
    anonymous: boolean;
  } | null>(null);
  const active = chats.find((chat) => chat.id === activeId) ?? chats[0];

  useEffect(() => {
    let cancelled = false;
    async function restoreWorkspace() {
      const { data } = await supabase.auth.getUser();
      const user = data.user;
      if (!user || cancelled) return;
      setAccount({
        id: user.id,
        label: user.phone ?? user.email ?? "Signed-in account",
        anonymous: Boolean(user.is_anonymous),
      });
      const { data: conversations } = await supabase
        .from("conversations")
        .select("id,title,updated_at")
        .order("updated_at", { ascending: false });
      if (!conversations?.length || cancelled) return;
      const ids = conversations.map((conversation) => conversation.id);
      const { data: messages } = await supabase
        .from("messages")
        .select("id,conversation_id,content")
        .in("conversation_id", ids)
        .order("created_at", { ascending: true });
      if (cancelled) return;
      const restored = conversations.map((conversation) => ({
        id: conversation.id,
        title: conversation.title,
        messages: (messages ?? [])
          .filter((message) => message.conversation_id === conversation.id)
          .map((message) => ({
            ...(message.content as Omit<Message, "id">),
            id: message.id,
          })),
      }));
      setChats(restored);
      setActiveId(restored[0].id);
    }
    void restoreWorkspace();
    return () => {
      cancelled = true;
    };
  }, [supabase]);

  async function ensureIdentity() {
    const { data } = await supabase.auth.getUser();
    let user = data.user;
    if (!user) {
      const anonymous = await supabase.auth.signInAnonymously();
      if (anonymous.error) throw anonymous.error;
      user = anonymous.data.user;
    }
    if (!user) throw new Error("Unable to create a secure guest session");
    setAccount({
      id: user.id,
      label: user.phone ?? user.email ?? "Guest session",
      anonymous: Boolean(user.is_anonymous),
    });
    return user;
  }

  function createChat() {
    const chat = newLocalChat();
    setChats((current) => [chat, ...current]);
    setActiveId(chat.id);
    setMobileSidebarOpen(false);
  }

  function selectChat(id: string) {
    setActiveId(id);
    setMobileSidebarOpen(false);
  }

  async function sendMessage(text: string) {
    const value = text.trim();
    if (!value || isSending) return;
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text: value,
    };
    const targetChatId = activeId;
    const activeHistory = active.messages.slice(-23).map((message) => ({
      role: message.role,
      content: message.text,
    }));
    setChats((current) =>
      current.map((chat) =>
        chat.id === targetChatId
          ? {
              ...chat,
              title:
                chat.messages.length === 0
                  ? `${value.slice(0, 42)}${value.length > 42 ? "…" : ""}`
                  : chat.title,
              messages: [...chat.messages, userMessage],
            }
          : chat,
      ),
    );
    setInput("");
    setSendError(null);
    setIsSending(true);

    const nextTitle =
      active.messages.length === 0
        ? `${value.slice(0, 42)}${value.length > 42 ? "…" : ""}`
        : active.title;
    const persistence = ensureIdentity().then(async (user) => {
      const { error: conversationError } = await supabase
        .from("conversations")
        .upsert(
          { id: targetChatId, owner_id: user.id, title: nextTitle },
          { onConflict: "id" },
        );
      if (conversationError) throw conversationError;
      const { error: messageError } = await supabase.from("messages").insert({
        id: userMessage.id,
        conversation_id: targetChatId,
        owner_id: user.id,
        role: "user",
        content: { role: userMessage.role, text: userMessage.text },
      });
      if (messageError) throw messageError;
      return user;
    });

    try {
      const [response, user] = await Promise.all([
        fetch("/api/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            messages: [...activeHistory, { role: "user", content: value }],
          }),
        }),
        persistence.catch(() => null),
      ]);
      if (!response.ok) throw new Error("Chat request failed");
      const result = (await response.json()) as VisaApiResult;
      const nextQuestion = result.answer.followUpQuestions[0];
      const reply: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: nextQuestion
          ? `${result.answer.summary}\n\n${nextQuestion}`
          : result.answer.summary,
        answer: result.answer,
        workflow: result.workflow,
        sources: result.sources,
        generated: result.generated,
      };
      setChats((current) =>
        current.map((chat) =>
          chat.id === targetChatId
            ? { ...chat, messages: [...chat.messages, reply] }
            : chat,
        ),
      );
      if (user) {
        const { error: replyError } = await supabase.from("messages").insert({
          id: reply.id,
          conversation_id: targetChatId,
          owner_id: user.id,
          role: "assistant",
          content: {
            role: reply.role,
            text: reply.text,
            answer: reply.answer,
            workflow: reply.workflow,
            sources: reply.sources,
            generated: reply.generated,
          },
        });
        if (replyError) {
          setSendError(
            "Your answer is ready, but it could not be saved to account history.",
          );
        }
      } else {
        setSendError(
          "Your answer is ready, but this conversation is only stored on this device until account service is available.",
        );
      }
    } catch {
      setSendError(
        "The visa assistant is unavailable right now. Please try again in a moment.",
      );
    } finally {
      setIsSending(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(input);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(input);
    }
  }

  return (
    <main className={styles.workspace}>
      <button
        className={`${styles.scrim} ${mobileSidebarOpen ? styles.scrimVisible : ""}`}
        onClick={() => setMobileSidebarOpen(false)}
        aria-label="Close conversation menu"
        type="button"
      />
      <aside
        className={`${styles.sidebar} ${sidebarOpen ? "" : styles.sidebarClosed} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ""}`}
        aria-label="Conversation history"
      >
        <div className={styles.sidebarInner}>
          <div className={styles.brandRow}>
            <Link href="/" className={styles.brand}>
              <span>
                <Icon name="shield" size={15} />
              </span>
              Uzbekistan OS
            </Link>
            <button
              type="button"
              onClick={() => {
                setSidebarOpen(false);
                setMobileSidebarOpen(false);
              }}
              className={styles.iconButton}
              aria-label="Collapse conversation menu"
            >
              <Icon name="panel" />
            </button>
          </div>
          <div className={styles.newChatWrap}>
            <button
              type="button"
              onClick={createChat}
              className={styles.newChat}
            >
              <Icon name="plus" size={15} />
              New chat
            </button>
          </div>
          <nav className={styles.history} aria-label="Saved conversations">
            <p>Today</p>
            {chats.slice(0, 1).map((chat) => (
              <button
                type="button"
                key={chat.id}
                onClick={() => selectChat(chat.id)}
                aria-current={chat.id === activeId ? "page" : undefined}
                className={chat.id === activeId ? styles.chatActive : ""}
              >
                {chat.title}
              </button>
            ))}
            {chats.length > 1 ? (
              <>
                <p>Previous</p>
                {chats.slice(1).map((chat) => (
                  <button
                    type="button"
                    key={chat.id}
                    onClick={() => selectChat(chat.id)}
                    aria-current={chat.id === activeId ? "page" : undefined}
                    className={chat.id === activeId ? styles.chatActive : ""}
                  >
                    {chat.title}
                  </button>
                ))}
              </>
            ) : null}
          </nav>
          <div className={styles.account}>
            <div className={styles.avatar}>
              {account?.anonymous === false ? "U" : "V"}
            </div>
            <div>
              <strong>
                {account?.anonymous === false ? "Your account" : "Visitor"}
              </strong>
              <span>{account?.label ?? "Guest access"}</span>
            </div>
            <Link
              className={styles.accountLink}
              href={account?.anonymous === false ? "/account" : "/signup"}
            >
              {account?.anonymous === false ? "Manage" : "Save"}
            </Link>
          </div>
        </div>
      </aside>

      <section className={styles.mainPanel} aria-label="Visa assistant">
        <header className={styles.topbar}>
          <div>
            <button
              type="button"
              onClick={() => {
                setSidebarOpen(true);
                setMobileSidebarOpen(true);
              }}
              className={`${styles.iconButton} ${sidebarOpen ? styles.desktopHidden : ""}`}
              aria-label="Open conversation menu"
            >
              <Icon name="panel" />
            </button>
            <span>Visa Assistant</span>
            <em>Grounded GPT</em>
          </div>
          <Link
            aria-label={
              account?.anonymous === false ? "Open account" : "Create account"
            }
            href={account?.anonymous === false ? "/account" : "/signup"}
            className={styles.avatar}
          >
            {account?.anonymous === false ? "U" : "V"}
          </Link>
        </header>

        <div className={styles.messages}>
          {active.messages.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyImage}>
                <Image
                  src="/landing/hero-background.avif"
                  fill
                  sizes="(max-width: 760px) 92vw, 680px"
                  alt="Tashkent skyline at sunset"
                  priority
                />
              </div>
              <div className={styles.emptyCopy}>
                <p className={styles.kicker}>Your visa workspace</p>
                <h1>
                  Clear visa guidance
                  <br />
                  for Uzbekistan
                </h1>
                <p>
                  Ask about entry routes, documents, application steps,
                  processing time, fees, and arrival registration.
                </p>
              </div>
              <div className={styles.suggestions}>
                {suggestions.map(([icon, text]) => (
                  <button
                    key={text}
                    type="button"
                    disabled={isSending}
                    onClick={() => void sendMessage(text)}
                  >
                    <span aria-hidden="true">{icon}</span>
                    {text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className={styles.thread}>
              {active.messages.map((message) => (
                <article
                  key={message.id}
                  className={`${styles.message} ${message.role === "user" ? styles.userMessage : styles.assistantMessage}`}
                >
                  <div className={styles.messageAvatar}>
                    {message.role === "user" ? (
                      "V"
                    ) : (
                      <Icon name="shield" size={15} />
                    )}
                  </div>
                  <div className={styles.messageContent}>
                    {message.answer?.status === "answered" ? null : (
                      <div className={styles.messageText}>
                        <MessageResponse>{message.text}</MessageResponse>
                      </div>
                    )}
                    {message.answer ? (
                      <GeneratedAnswerCard message={message} />
                    ) : null}
                  </div>
                </article>
              ))}
              {isSending ? (
                <div className={styles.thinking} role="status">
                  <span className={styles.messageAvatar}>
                    <Icon name="shield" size={15} />
                  </span>
                  <div>
                    <i />
                    <i />
                    <i />
                    <span>
                      Checking the visa workflow and reviewed sources…
                    </span>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        <footer className={styles.composerArea}>
          <form className={styles.composer} onSubmit={submit}>
            <label className={styles.srOnly} htmlFor="visa-question">
              Ask the visa assistant
            </label>
            <textarea
              id="visa-question"
              rows={1}
              value={input}
              disabled={isSending}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about visas or entry to Uzbekistan…"
            />
            <button
              type="submit"
              disabled={!input.trim() || isSending}
              aria-label="Send question"
            >
              <Icon name="send" size={15} />
            </button>
          </form>
          {sendError ? (
            <p className={styles.composerError} role="alert">
              {sendError}
            </p>
          ) : (
            <p>
              GPT guidance is limited to reviewed evidence. Verify current rules
              at{" "}
              <a
                href="https://www.e-visa.gov.uz/"
                target="_blank"
                rel="noreferrer"
              >
                e-visa.gov.uz
              </a>{" "}
              and{" "}
              <a href="https://gov.uz/en/mfa" target="_blank" rel="noreferrer">
                gov.uz/mfa
              </a>
              .
            </p>
          )}
        </footer>
      </section>
    </main>
  );
}
