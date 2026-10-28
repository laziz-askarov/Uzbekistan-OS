import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { GuideList } from "@/components/site/guide-list";
import { JsonLd } from "@/components/site/json-ld";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { findAuthorProfile } from "@/lib/authors";
import {
  listPublishedPosts,
  SITE_URL,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import { OPERATOR_CITY, OPERATOR_NAME, SITE_NAME } from "@/lib/site";
import styles from "../author.module.css";

type AuthorPageProps = {
  params: Promise<{ slug: string }>;
};

async function loadPosts(): Promise<PublishedPostSummary[]> {
  try {
    return await listPublishedPosts({ limit: 100 });
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
}: AuthorPageProps): Promise<Metadata> {
  const { slug } = await params;
  const profile = findAuthorProfile(await loadPosts(), slug);
  if (!profile) return { title: `Author | ${SITE_NAME}` };
  const title = `${profile.name}, author at ${SITE_NAME} by ${OPERATOR_NAME}`;
  const description = `Guides to travelling in and living in Uzbekistan written by ${profile.name} for ${SITE_NAME}, published by ${OPERATOR_NAME} in ${OPERATOR_CITY}.`;
  return {
    title,
    description,
    alternates: { canonical: `${SITE_URL}/authors/${profile.slug}` },
    openGraph: {
      type: "profile",
      url: `${SITE_URL}/authors/${profile.slug}`,
      title,
      description,
    },
  };
}

export default async function AuthorPage({ params }: AuthorPageProps) {
  const { slug } = await params;
  const profile = findAuthorProfile(await loadPosts(), slug);
  if (!profile) notFound();

  const url = `${SITE_URL}/authors/${profile.slug}`;
  const person = {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": `${url}#person`,
    name: profile.name,
    url,
    jobTitle: "Author",
    worksFor: { "@id": `${SITE_URL}/#organization` },
    homeLocation: { "@type": "Place", name: `${OPERATOR_CITY}, Uzbekistan` },
  };

  return (
    <div>
      <SiteHeader current="/about" />
      <main className="page-main">
        <JsonLd data={person} />
        <section className={styles.intro}>
          <p className={styles.role}>
            Author at {SITE_NAME} by {OPERATOR_NAME}
          </p>
          <h1>{profile.name}</h1>
          <p>
            Writes guides for {SITE_NAME} from {OPERATOR_CITY}. Every guide
            lists the official source behind each rule and the date it was
            last verified. Read{" "}
            <Link href="/about#methodology">how the team verifies guides</Link>.
          </p>
        </section>
        <section aria-labelledby="author-guides-title">
          <p className={styles.count}>
            {profile.guideCount} published{" "}
            {profile.guideCount === 1 ? "guide" : "guides"}
          </p>
          <h2 id="author-guides-title" className="visually-hidden">
            Guides by {profile.name}
          </h2>
          <GuideList posts={profile.posts} labelledBy="author-guides-title" />
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
