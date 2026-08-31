import type { Metadata } from "next";
import Link from "next/link";
import { listPublishedPosts, SITE_URL } from "@/lib/editorial-content";
import styles from "./blog.module.css";

export const metadata: Metadata = {
  title: "Uzbekistan guides, tourism, business and laws | Uzbekistan OS",
  description:
    "Reviewed guides about visiting, living, and doing business in Uzbekistan, with transparent authorship and source links.",
  alternates: { canonical: `${SITE_URL}/blog` },
  openGraph: {
    type: "website",
    url: `${SITE_URL}/blog`,
    title: "Uzbekistan guides | Uzbekistan OS",
    description:
      "Reviewed guides about visiting, living, and doing business in Uzbekistan.",
    images: [
      {
        url: `${SITE_URL}/blog/opengraph-image`,
        width: 1200,
        height: 630,
        alt: "Uzbekistan OS reviewed guides",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Uzbekistan guides | Uzbekistan OS",
    description:
      "Reviewed guides about visiting, living, and doing business in Uzbekistan.",
    images: [`${SITE_URL}/blog/opengraph-image`],
  },
};

const domains = [
  ["", "All"],
  ["tourism", "Tourism"],
  ["business-registration", "Business"],
  ["immigration", "Immigration"],
  ["everyday-living", "Living"],
  ["healthcare", "Healthcare"],
] as const;

type BlogIndexProps = {
  searchParams: Promise<{ domain?: string }>;
};

function displayDomain(value: string | null) {
  return value?.replaceAll("-", " ") ?? "Uzbekistan";
}

export default async function BlogIndex({ searchParams }: BlogIndexProps) {
  const { domain } = await searchParams;
  const selectedDomain = domains.some(([value]) => value === domain)
    ? domain
    : undefined;
  const posts = await listPublishedPosts({
    domain: selectedDomain || undefined,
    limit: 100,
  });

  return (
    <>
      <section className={styles.indexHero}>
        <p className={styles.eyebrow}>Uzbekistan, explained clearly</p>
        <h1>Practical guides built on reviewed sources.</h1>
        <p>
          Explore travel, business, immigration, healthcare, and everyday-life
          guidance with visible authorship, publication dates, and source
          lineage.
        </p>
      </section>

      <nav className={styles.filters} aria-label="Filter guides by topic">
        {domains.map(([value, label]) => (
          <Link
            aria-current={(selectedDomain ?? "") === value ? "page" : undefined}
            href={value ? `/blog?domain=${value}` : "/blog"}
            key={value || "all"}
          >
            {label}
          </Link>
        ))}
      </nav>

      {posts.length ? (
        <section className={styles.postGrid} aria-label="Published guides">
          {posts.map((post) => (
            <Link
              className={styles.postCard}
              href={`/blog/${post.slug}`}
              key={post.id}
            >
              <div className={styles.cardMeta}>
                <span className={styles.category}>
                  {displayDomain(post.domain_slug)}
                </span>
                <span>{post.language_code.toUpperCase()}</span>
                <time dateTime={post.published_at}>
                  {new Intl.DateTimeFormat("en", {
                    dateStyle: "medium",
                  }).format(new Date(post.published_at))}
                </time>
              </div>
              <h2>{post.title}</h2>
              <p>{post.summary}</p>
              <span className={styles.readMore}>Read guide →</span>
            </Link>
          ))}
        </section>
      ) : (
        <section className={styles.empty}>
          <h2>No published guides in this topic yet</h2>
          <p>
            Approved articles will appear here as soon as they are published.
          </p>
        </section>
      )}
    </>
  );
}
