import Link from "next/link";
import type { PublishedPostSummary } from "@/lib/editorial-content";
import styles from "./guide-list.module.css";

type GuideListProps = {
  posts: PublishedPostSummary[];
  labelledBy?: string;
};

export function formatVerifiedDate(value: string, locale = "en") {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
}

function VerifiedMark() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle cx="8" cy="8" r="7" fill="currentColor" opacity="0.15" />
      <path
        d="M4.5 8.2l2.3 2.3 4.7-4.9"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function GuideList({ posts, labelledBy }: GuideListProps) {
  return (
    <ul className={styles.list} aria-labelledby={labelledBy}>
      {posts.map((post) => {
        const titleId = `guide-${post.id}`;
        return (
          <li className={styles.item} key={post.id} lang={post.language_code}>
            <Link
              className={styles.row}
              href={`/blog/${post.slug}`}
              aria-labelledby={titleId}
            >
              <h3 id={titleId}>{post.title}</h3>
              <span className={styles.verified}>
                <VerifiedMark />
                Verified{" "}
                <time dateTime={post.updated_at}>
                  {formatVerifiedDate(post.updated_at, post.language_code)}
                </time>
              </span>
              <p>{post.summary}</p>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
