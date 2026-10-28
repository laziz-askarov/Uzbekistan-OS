import type { Metadata } from "next";
import Link from "next/link";
import { GuideList } from "@/components/site/guide-list";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import {
  listPublishedPosts,
  SITE_URL,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import { groupTravelGuides } from "@/lib/guide-clusters";
import { OPERATOR_NAME } from "@/lib/site";
import styles from "../hub.module.css";

const title = "Uzbekistan travel guides, verified and dated | Uzbekistan OS";
const description =
  "Practical guides for a first trip to Uzbekistan: visa rules, registration, money, SIM cards, safety, trains, where to go and what to eat. Each guide shows its verification date and official sources.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${SITE_URL}/travel` },
  openGraph: {
    type: "website",
    url: `${SITE_URL}/travel`,
    title,
    description,
  },
};

async function loadGuides(): Promise<PublishedPostSummary[]> {
  try {
    return await listPublishedPosts({ language: "en", limit: 100 });
  } catch {
    return [];
  }
}

export default async function TravelHub() {
  const guides = await loadGuides();
  const clusters = groupTravelGuides(guides);
  const total = clusters.reduce((count, group) => count + group.posts.length, 0);

  return (
    <div>
      <SiteHeader current="/travel" />
      <main className="page-main">
        <section className={styles.intro}>
          <h1>Uzbekistan travel guides</h1>
          <p>
            Everything that has to work on a trip to Uzbekistan, from the
            entry rule for your passport to the train you take to Khiva. Each
            guide shows the date we last verified it and links the official
            source behind every rule.
          </p>
        </section>

        {total === 0 ? (
          <p className={styles.empty}>
            The guide library is loading. See{" "}
            <Link href="/blog">all published guides</Link> in the meantime.
          </p>
        ) : null}

        {clusters.map((group) => (
          <section
            className="band"
            id={group.id}
            key={group.id}
            aria-labelledby={`${group.id}-title`}
          >
            <div className="band-label">
              <h2 id={`${group.id}-title`}>{group.title}</h2>
              <p>{group.description}</p>
            </div>
            <div>
              {group.posts.length ? (
                <GuideList posts={group.posts} labelledBy={`${group.id}-title`} />
              ) : (
                <p className={styles.empty}>
                  No published guides in this group yet.
                </p>
              )}
            </div>
          </section>
        ))}

        <aside className={styles.help} aria-label="Trip planning service">
          <p>
            <strong>Rather have it arranged?</strong>
            {OPERATOR_NAME}, the company behind these guides, plans private
            trips from Tashkent. Reply comes by email with a dated plan and
            prices.
          </p>
          <Link className="btn btn-service" href="/trips">
            Plan my trip
          </Link>
        </aside>
      </main>
      <SiteFooter />
    </div>
  );
}
