import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { buildAuthorProfiles } from "@/lib/authors";
import {
  listPublishedPosts,
  SITE_URL,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import {
  CONTACT_EMAIL,
  OPERATOR_CITY,
  OPERATOR_NAME,
  SITE_NAME,
} from "@/lib/site";
import styles from "./about.module.css";

const title =
  "About Uzbekistan OS and Kebab Travel: who writes the guides and how we verify them";
const description =
  "Uzbekistan OS is published by Kebab Travel, a Tashkent travel company. Learn who writes the guides, how every rule is checked against an official source and dated, and how the guides stay independent of the trips we plan.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${SITE_URL}/about` },
  openGraph: { type: "website", url: `${SITE_URL}/about`, title, description },
};

async function loadPosts(): Promise<PublishedPostSummary[]> {
  try {
    return await listPublishedPosts({ limit: 100 });
  } catch {
    return [];
  }
}

export default async function AboutPage() {
  const authors = buildAuthorProfiles(await loadPosts());

  return (
    <div>
      <SiteHeader current="/about" />
      <main className="page-main">
        <section className={styles.intro}>
          <h1>Guides you can check, from people who live here.</h1>
          <p>
            {SITE_NAME} is published by {OPERATOR_NAME}, a travel company in{" "}
            {OPERATOR_CITY}. We write the reference we wished existed when
            friends from the US and Europe asked us how Uzbekistan actually
            works: dated, sourced, and honest about what we could not confirm.
          </p>
        </section>

        <section className="band" id="who" aria-labelledby="who-title">
          <div className="band-label">
            <h2 id="who-title">Who we are</h2>
          </div>
          <div className="prose">
            <p>
              {OPERATOR_NAME} plans private trips to Uzbekistan for travellers
              from North America and Europe. The company is based in{" "}
              {OPERATOR_CITY} and the same team writes and maintains the guides
              on this site. The guides are free and do not require an account.
            </p>
            <p>
              The site started in 2026 as a reference for the official
              procedures foreigners meet in Uzbekistan. It now leads with
              travel, with the <Link href="/living">Living in Uzbekistan</Link>{" "}
              guides kept for people who stay longer.
            </p>
          </div>
        </section>

        <section className="band" id="authors" aria-labelledby="authors-title">
          <div className="band-label">
            <h2 id="authors-title">Our authors</h2>
            <p>
              Each guide carries a named author. Profiles list that
              author&rsquo;s published guides.
            </p>
          </div>
          <div>
            {authors.length ? (
              <ul className={styles.authors}>
                {authors.map((author) => (
                  <li key={author.slug}>
                    <Link href={`/authors/${author.slug}`}>
                      <strong>{author.name}</strong>
                      <span>
                        {author.guideCount} published{" "}
                        {author.guideCount === 1 ? "guide" : "guides"}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="prose">
                Author profiles appear here as guides are published. See{" "}
                <Link href="/blog">all guides</Link>.
              </p>
            )}
          </div>
        </section>

        <section
          className="band"
          id="methodology"
          aria-labelledby="methodology-title"
        >
          <div className="band-label">
            <h2 id="methodology-title">How we verify</h2>
            <p>
              The process behind the &ldquo;Verified&rdquo; date on every guide.
            </p>
          </div>
          <ul className={styles.checks}>
            <li>
              <strong>Official source first.</strong> Rules, fees and deadlines
              come from the ministry, agency or operator that sets them. The
              guide links that page and names the organisation.
            </li>
            <li>
              <strong>Dated checks.</strong> The verification date is the day a
              named author last compared the guide with the source. Rules
              change; the date tells you how fresh the page is.
            </li>
            <li>
              <strong>Reviewed before publication.</strong> A second person
              reviews every guide and every revision before it goes live. The
              editorial version number is shown at the end of each guide.
            </li>
            <li>
              <strong>Plain about uncertainty.</strong> If we could not confirm
              something, the guide says so rather than guessing. Advice written
              for one nationality is labelled as such.
            </li>
            <li>
              <strong>Checked on the ground.</strong> Where it matters, we
              confirm at the airport, the station or the bank, not only on a
              website.
            </li>
            <li>
              <strong>Machine-readable.</strong> Every guide has a Markdown
              edition and structured data so assistants and search engines can
              quote it with its date and sources. See{" "}
              <a href="/llms.txt">llms.txt</a>.
            </li>
          </ul>
        </section>

        <section
          className="band"
          id="independence"
          aria-labelledby="independence-title"
        >
          <div className="band-label">
            <h2 id="independence-title">Editorial independence</h2>
          </div>
          <div className="prose">
            <p>
              {OPERATOR_NAME} sells trips. The guides do not. A guide never
              changes because of what we offer, and we do not place affiliate
              links in guides about rules, prices or safety.
            </p>
            <p>
              The trip service appears only in clearly labelled boxes and on the{" "}
              <Link href="/trips">Plan my trip</Link> page. Hotel, guide and
              operator recommendations, when we make them, follow the same rule:
              named, dated and explained.
            </p>
          </div>
        </section>

        <section className="band" id="contact" aria-labelledby="contact-title">
          <div className="band-label">
            <h2 id="contact-title">Contact</h2>
          </div>
          <div className="prose">
            <p>
              Corrections, questions about a guide, or press:{" "}
              <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Trip
              planning: use the <Link href="/trips">inquiry form</Link>.
            </p>
            <p>
              {OPERATOR_NAME}, {OPERATOR_CITY}, Uzbekistan.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
