import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MarkdownContent } from "@/components/editorial/markdown-content";
import {
  getPublishedPost,
  publicPostUrl,
  SITE_URL,
  type PublishedPost,
} from "@/lib/editorial-content";
import styles from "../blog.module.css";

type ArticlePageProps = { params: Promise<{ slug: string }> };
type FaqItem = { question: string; answer: string };

function safeAbsoluteUrl(value: string | null, fallback: string) {
  if (!value) return fallback;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.toString()
      : fallback;
  } catch {
    return fallback;
  }
}

function faqItems(post: PublishedPost): FaqItem[] {
  const candidate = post.structured_content.faq ?? post.structured_content.faqs;
  if (!Array.isArray(candidate)) return [];
  return candidate.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const question = "question" in item ? item.question : null;
    const answer = "answer" in item ? item.answer : null;
    return typeof question === "string" && typeof answer === "string"
      ? [{ question, answer }]
      : [];
  });
}

function takeaways(post: PublishedPost) {
  const candidate = post.structured_content.key_takeaways;
  return Array.isArray(candidate)
    ? candidate.filter((item): item is string => typeof item === "string")
    : [];
}

function formatReviewDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "long" }).format(
    new Date(value),
  );
}

function languageName(languageCode: string) {
  return (
    {
      uz: "O‘zbekcha",
      en: "English",
      ru: "Русский",
    }[languageCode] ?? languageCode.toUpperCase()
  );
}

function jsonLd(post: PublishedPost, canonical: string, faqs: FaqItem[]) {
  const authorUrl = safeAbsoluteUrl(
    post.author.profile_url,
    `${SITE_URL}/blog`,
  );
  const imageUrl = post.hero_image_url
    ? safeAbsoluteUrl(post.hero_image_url, "")
    : "";
  const graph: Array<Record<string, unknown>> = [
    {
      "@type": "BlogPosting",
      "@id": `${canonical}#article`,
      headline: post.title,
      description: post.seo_description ?? post.summary,
      mainEntityOfPage: canonical,
      datePublished: post.published_at,
      dateModified: post.updated_at,
      inLanguage: post.language_code,
      articleSection: post.domain_slug ?? "Uzbekistan",
      author: {
        "@type": "Person",
        name: post.author.name,
        url: authorUrl,
      },
      publisher: {
        "@type": "Organization",
        name: "Uzbekistan OS",
        url: SITE_URL,
      },
      citation: post.sources.map((source) => source.url),
      ...(imageUrl
        ? {
            image: [imageUrl],
          }
        : {}),
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Uzbekistan OS",
          item: SITE_URL,
        },
        {
          "@type": "ListItem",
          position: 2,
          name: "Guides",
          item: `${SITE_URL}/blog`,
        },
        {
          "@type": "ListItem",
          position: 3,
          name: post.title,
          item: canonical,
        },
      ],
    },
  ];
  if (faqs.length) {
    graph.push({
      "@type": "FAQPage",
      mainEntity: faqs.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: { "@type": "Answer", text: item.answer },
      })),
    });
  }
  return JSON.stringify({
    "@context": "https://schema.org",
    "@graph": graph,
  }).replace(/</g, "\\u003c");
}

export async function generateMetadata({
  params,
}: ArticlePageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPublishedPost(slug);
  if (!post) return { title: "Guide not found | Uzbekistan OS" };

  const publicUrl = publicPostUrl(post.slug);
  const canonical = safeAbsoluteUrl(post.canonical_url, publicUrl);
  const languageAlternates = Object.fromEntries(
    post.translations.map((translation) => [
      translation.language_code,
      publicPostUrl(translation.slug),
    ]),
  );
  const defaultTranslation =
    post.translations.find(
      (translation) => translation.language_code === "en",
    ) ?? post.translations[0];
  if (defaultTranslation) {
    languageAlternates["x-default"] = publicPostUrl(defaultTranslation.slug);
  }
  const image = post.hero_image_url
    ? safeAbsoluteUrl(post.hero_image_url, "")
    : "";
  const generatedImage = `${publicUrl}/opengraph-image`;
  const socialImages = [
    {
      url: generatedImage,
      width: 1200,
      height: 630,
      alt: post.hero_image_alt ?? `${post.title} — Uzbekistan OS`,
    },
    ...(image ? [{ url: image, alt: post.hero_image_alt ?? post.title }] : []),
  ];

  return {
    title: `${post.seo_title ?? post.title} | Uzbekistan OS`,
    description: post.seo_description ?? post.summary,
    alternates: {
      canonical,
      languages: languageAlternates,
      types: { "text/markdown": `${publicUrl}/markdown` },
    },
    openGraph: {
      type: "article",
      url: canonical,
      title: post.seo_title ?? post.title,
      description: post.seo_description ?? post.summary,
      publishedTime: post.published_at,
      modifiedTime: post.updated_at,
      authors: [post.author.name],
      locale: post.language_code,
      images: socialImages,
    },
    twitter: {
      card: "summary_large_image",
      title: post.seo_title ?? post.title,
      description: post.seo_description ?? post.summary,
      images: [generatedImage],
    },
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const post = await getPublishedPost(slug);
  if (!post) notFound();

  const canonical = safeAbsoluteUrl(
    post.canonical_url,
    publicPostUrl(post.slug),
  );
  const faqs = faqItems(post);
  const keyTakeaways = takeaways(post);
  const published = new Intl.DateTimeFormat("en", { dateStyle: "long" }).format(
    new Date(post.published_at),
  );
  const updated = new Intl.DateTimeFormat("en", { dateStyle: "long" }).format(
    new Date(post.updated_at),
  );

  return (
    <article className={styles.article} lang={post.language_code}>
      <script
        dangerouslySetInnerHTML={{ __html: jsonLd(post, canonical, faqs) }}
        type="application/ld+json"
      />
      <nav className={styles.breadcrumbs} aria-label="Breadcrumb">
        <Link href="/">Home</Link> / <Link href="/blog">Guides</Link> /{" "}
        <span aria-current="page">{post.title}</span>
      </nav>

      <header className={styles.articleHero}>
        <div className={styles.articleMeta}>
          <span className={styles.category}>
            {post.domain_slug?.replaceAll("-", " ") ?? "Uzbekistan"}
          </span>
          <span>{post.content_type.replaceAll("_", " ")}</span>
          <span>{post.language_code.toUpperCase()}</span>
        </div>
        <h1>{post.title}</h1>
        <p className={styles.dek}>{post.summary}</p>
        <div className={styles.articleMeta}>
          <span>By {post.author.name}</span>
          <time dateTime={post.published_at}>Published {published}</time>
          {post.updated_at !== post.published_at ? (
            <time dateTime={post.updated_at}>Updated {updated}</time>
          ) : null}
        </div>
        {post.translations.length > 1 ? (
          <nav className={styles.languageLinks} aria-label="Article languages">
            {post.translations.map((translation) => (
              <Link
                href={`/blog/${translation.slug}`}
                hrefLang={translation.language_code}
                key={translation.language_code}
              >
                {languageName(translation.language_code)}
              </Link>
            ))}
          </nav>
        ) : null}
      </header>

      {keyTakeaways.length ? (
        <section
          className={styles.takeaways}
          aria-labelledby="takeaways-heading"
        >
          <h2 id="takeaways-heading">Key takeaways</h2>
          <ul>
            {keyTakeaways.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className={styles.articleBody}>
        <MarkdownContent markdown={post.body_markdown} />
      </div>

      {faqs.length ? (
        <section className={styles.faq} aria-labelledby="faq-heading">
          <h2 id="faq-heading">Frequently asked questions</h2>
          {faqs.map((item) => (
            <details key={item.question}>
              <summary>{item.question}</summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </section>
      ) : null}

      {post.sources.length ? (
        <section className={styles.sources} aria-labelledby="sources-heading">
          <h2 id="sources-heading">Sources and review trail</h2>
          <ol className={styles.sourceList}>
            {post.sources.map((source) => (
              <li key={`${source.source_id}-${source.locator}`}>
                <a href={source.url} rel="noreferrer" target="_blank">
                  {source.title}
                </a>
                <span>{source.organization}</span>
                <span>{source.locator}</span>
                {source.document_title ? (
                  <span>Reviewed knowledge: {source.document_title}</span>
                ) : null}
                {source.reviewed_at ? (
                  <time dateTime={source.reviewed_at}>
                    Knowledge reviewed {formatReviewDate(source.reviewed_at)}
                  </time>
                ) : null}
              </li>
            ))}
          </ol>
          <Link
            className={styles.machineLink}
            href={`/blog/${post.slug}/markdown`}
          >
            View machine-readable Markdown →
          </Link>
        </section>
      ) : null}

      <section className={styles.authorBox} aria-labelledby="author-heading">
        <h2 id="author-heading">About the author</h2>
        <p>
          <strong>{post.author.name}</strong>
          {post.author.bio ? ` — ${post.author.bio}` : ""}
        </p>
      </section>

      <p className={styles.reviewNote}>
        Editorial version {post.version_number}. This page is independent
        informational guidance and links to the sources reviewed for this
        edition.
      </p>
    </article>
  );
}
