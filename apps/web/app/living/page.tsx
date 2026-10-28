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
import { groupLivingGuides, LIVING_DOMAINS } from "@/lib/guide-clusters";
import styles from "../hub.module.css";

const title = "Living in Uzbekistan: residence, work, business and healthcare | Uzbekistan OS";
const description =
  "Verified guides to the official procedures foreigners meet when staying longer in Uzbekistan: registration, residence permits, work, starting a company, banking, renting and healthcare.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${SITE_URL}/living` },
  openGraph: {
    type: "website",
    url: `${SITE_URL}/living`,
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

export default async function LivingHub() {
  const guides = await loadGuides();
  const groups = groupLivingGuides(guides);
  const published = new Map(groups.map((group) => [group.slug, group.posts]));

  return (
    <div>
      <SiteHeader current="/living" />
      <main className="page-main">
        <section className={styles.intro}>
          <h1>Living in Uzbekistan</h1>
          <p>
            Staying longer than a holiday brings official procedures: stay
            registration, residence permits, work authorization, company
            formation, bank accounts and healthcare. These guides follow the
            same rule as the travel guides: dated, sourced, reviewed before
            publication.
          </p>
        </section>

        {groups.length === 0 ? (
          <p className={styles.empty}>
            Living guides are being prepared. See{" "}
            <Link href="/blog">all published guides</Link> for what is
            available now.
          </p>
        ) : null}

        {LIVING_DOMAINS.map((domain) => {
          const posts = published.get(domain.slug) ?? [];
          return (
            <section
              className="band"
              id={domain.slug}
              key={domain.slug}
              aria-labelledby={`${domain.slug}-title`}
            >
              <div className="band-label">
                <h2 id={`${domain.slug}-title`}>{domain.title}</h2>
                <p>{domain.description}</p>
              </div>
              <div>
                {posts.length ? (
                  <GuideList posts={posts} labelledBy={`${domain.slug}-title`} />
                ) : (
                  <p className={styles.empty}>
                    No published guides in this area yet.
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </main>
      <SiteFooter />
    </div>
  );
}
