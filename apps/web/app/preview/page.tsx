import type { Metadata } from "next";
import Link from "next/link";
import { AnorMosaic } from "@/components/brand/anor-mosaic";
import { SectionIcon } from "@/components/brand/section-icon";
import { SeedCluster } from "@/components/brand/seed-cluster";
import { TileRule } from "@/components/brand/tile-rule";
import { formatVerifiedDate } from "@/components/site/guide-list";
import {
  groupBySection,
  sectionForPost,
  type BrandSectionGroup,
} from "@/lib/brand-sections";
import {
  listPublishedPosts,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import { latestVerification, LIVING_DOMAINS } from "@/lib/guide-clusters";
import {
  CONTACT_EMAIL,
  FOOTER_NAVIGATION,
  OPERATOR_NAME,
  POLICY_NAVIGATION,
  SITE_NAME,
} from "@/lib/site";
import styles from "./preview.module.css";

export const metadata: Metadata = {
  title: "Brand preview | Uzbekistan OS",
  robots: { index: false, follow: false },
};

const FIRST_TRIP_GUIDE = "/blog/visiting-uzbekistan-first-time";
const WHERE_TO_STAY_GUIDE = "/blog/where-to-stay-in-uzbekistan";

const NAV = [
  { href: "/travel", label: "Travel guides", section: "transport" },
  { href: "/living", label: "Living", section: "living" },
  { href: "/about", label: "About", section: "planning" },
] as const;

const ROUTE = [
  {
    city: "Tashkent",
    days: "1 to 2 days",
    copy: "The capital and almost every arrival point. Chorsu bazaar, a metro worth riding for its stations, and the trains west.",
  },
  {
    city: "Samarkand",
    days: "2 days",
    copy: "Registan, Shah-i-Zinda and Gur-e-Amir. Two hours from Tashkent on the Afrosiyob.",
  },
  {
    city: "Bukhara",
    days: "2 days",
    copy: "A walkable old town of madrasas, trading domes and the Kalon minaret. The best evenings on the route.",
  },
  {
    city: "Khiva",
    days: "1 to 2 days",
    copy: "Itchan Kala, a walled city you can cross in fifteen minutes. The far end of the classic journey.",
  },
];

function shortTitle(title: string) {
  return title.split(":")[0].trim();
}

async function loadGuides(): Promise<PublishedPostSummary[]> {
  try {
    return await listPublishedPosts({ language: "en", limit: 100 });
  } catch {
    return [];
  }
}

function countLabel(group: BrandSectionGroup) {
  if (group.section.id === "living" && group.posts.length === 0) {
    return `${LIVING_DOMAINS.length} topics`;
  }
  const n = group.posts.length;
  return n === 1 ? "1 guide" : `${n} guides`;
}

export default async function BrandPreview() {
  const guides = await loadGuides();
  const groups = groupBySection(guides);
  const latest = [...guides]
    .sort((a, b) => b.published_at.localeCompare(a.published_at))
    .slice(0, 3);
  const verifiedAt = latestVerification(guides);

  return (
    <div className={styles.page}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>

      <header className={styles.header}>
        <div className={styles.inner}>
          <Link
            className={styles.logo}
            href="/preview"
            aria-label={`${SITE_NAME} home`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/anor-horizontal.svg"
              alt=""
              width={157}
              height={40}
              fetchPriority="high"
            />
          </Link>
          <nav className={styles.nav} aria-label="Main navigation">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                data-section={item.section}
              >
                <i className={styles.tile} aria-hidden="true" />
                {item.label}
              </Link>
            ))}
          </nav>
          <Link
            className={`${styles.btn} ${styles.btnSecondary} ${styles.headerCta}`}
            href="/trips"
          >
            Plan my trip
          </Link>
        </div>
      </header>

      <main id="main">
        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={`${styles.inner} ${styles.heroGrid}`}>
            <div className={styles.heroCopy}>
              <h1 className={styles.heroTitle} id="hero-title">
                Everything you need to know about Uzbekistan.
              </h1>
              <p className={styles.deck}>
                Visas, money, trains, where to stay and how to live here,
                written by a team in Tashkent. Every guide names the official
                source and shows the date we last checked it.
              </p>
              <div className={styles.actions}>
                <Link
                  className={`${styles.btn} ${styles.btnPrimary}`}
                  href={FIRST_TRIP_GUIDE}
                >
                  Start with the first-trip guide
                </Link>
                <Link
                  className={`${styles.btn} ${styles.btnGhost}`}
                  href="/about#methodology"
                >
                  How we check facts
                </Link>
              </div>
              <p className={styles.dateline} data-section="living">
                <i className={styles.tile} aria-hidden="true" />
                {verifiedAt ? (
                  <span>
                    Last checked{" "}
                    <time dateTime={verifiedAt}>
                      {formatVerifiedDate(verifiedAt)}
                    </time>
                    . {guides.length} guides in English, each with its official
                    source.
                  </span>
                ) : (
                  <span>Every guide shows the date it was last checked.</span>
                )}
              </p>
            </div>
            <div className={styles.heroMark}>
              <AnorMosaic />
            </div>
          </div>
        </section>

        <TileRule section="visas" />

        <section className={styles.index} aria-labelledby="index-title">
          <div className={styles.inner}>
            <h2 className={styles.h2} id="index-title">
              Guides by section
            </h2>
            <ul className={styles.rows}>
              {groups.map((group) => (
                <li
                  className={styles.row}
                  data-section={group.section.id}
                  key={group.section.id}
                >
                  <div className={styles.rowHead}>
                    <SectionIcon
                      id={group.section.id}
                      className={styles.rowIcon}
                    />
                    <h3>
                      <Link href={group.section.href}>
                        <i className={styles.tile} aria-hidden="true" />
                        {group.section.title}
                      </Link>
                    </h3>
                    <span className={styles.count}>{countLabel(group)}</span>
                    <p>{group.section.description}</p>
                  </div>
                  <ul className={styles.rowGuides}>
                    {group.posts.map((post) => (
                      <li key={post.id}>
                        <Link href={`/blog/${post.slug}`}>
                          <span>{shortTitle(post.title)}</span>
                          <time dateTime={post.updated_at}>
                            {formatVerifiedDate(post.updated_at)}
                          </time>
                        </Link>
                      </li>
                    ))}
                    {group.section.id === "living" && group.posts.length === 0
                      ? LIVING_DOMAINS.map((domain) => (
                          <li key={domain.slug}>
                            <Link href={`/living#${domain.slug}`}>
                              <span>{domain.title}</span>
                            </Link>
                          </li>
                        ))
                      : null}
                    {group.section.id !== "living" &&
                    group.posts.length === 0 ? (
                      <li className={styles.empty}>Guides are being loaded.</li>
                    ) : null}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <TileRule section="transport" />

        <section className={styles.route} aria-labelledby="route-title">
          <div className={`${styles.inner} ${styles.routeGrid}`}>
            <figure className={styles.routePhoto}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/landing/hero-background.avif"
                alt="Tashkent at dusk, seen from above the city centre"
                width={1600}
                height={1000}
                loading="lazy"
                decoding="async"
              />
              <figcaption>
                Tashkent at dusk. Almost every trip starts in the capital.
              </figcaption>
            </figure>
            <div className={styles.routeCopy}>
              <h2 className={styles.h2} id="route-title">
                The classic route, west from Tashkent
              </h2>
              <p className={styles.lead}>
                Most first trips follow one line from the capital to the desert.
                Seven to ten days covers it without rushing, and the high-speed
                train does the long middle.
              </p>
              <ol className={styles.stops}>
                {ROUTE.map((stop) => (
                  <li key={stop.city}>
                    <strong>{stop.city}</strong>
                    <span>{stop.days}</span>
                    <p>{stop.copy}</p>
                  </li>
                ))}
              </ol>
              <div className={styles.actions}>
                <Link
                  className={`${styles.btn} ${styles.btnSecondary}`}
                  href={FIRST_TRIP_GUIDE}
                >
                  Read the seven-day route
                </Link>
                <Link
                  className={`${styles.btn} ${styles.btnGhost}`}
                  href={WHERE_TO_STAY_GUIDE}
                >
                  Where to stay
                </Link>
              </div>
            </div>
          </div>
        </section>

        <TileRule section="money" />

        <section className={styles.latest} aria-labelledby="latest-title">
          <div className={styles.inner}>
            <div className={styles.sectionHead}>
              <h2 className={styles.h2} id="latest-title">
                Latest guides
              </h2>
              <Link className={styles.more} href="/blog">
                All guides
              </Link>
            </div>
            {latest.length ? (
              <div className={styles.cards}>
                {latest.map((post) => {
                  const section = sectionForPost(post);
                  return (
                    <Link
                      className={styles.card}
                      data-section={section.id}
                      href={`/blog/${post.slug}`}
                      key={post.id}
                    >
                      <span className={styles.tag}>
                        <i className={styles.tile} aria-hidden="true" />
                        {section.title}
                      </span>
                      <h3>{post.title}</h3>
                      <p className={styles.meta}>
                        By {post.author_name}. Last checked{" "}
                        <time dateTime={post.updated_at}>
                          {formatVerifiedDate(post.updated_at)}
                        </time>
                      </p>
                      <span className={styles.tileRow} aria-hidden="true">
                        <i />
                        <i />
                        <i />
                        <i />
                      </span>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <p className={styles.emptyNote}>
                Published guides appear here. See{" "}
                <Link href="/blog">all guides</Link>.
              </p>
            )}
          </div>
        </section>

        <section
          className={styles.service}
          aria-labelledby="service-title"
          data-section="living"
        >
          <div className={`${styles.inner} ${styles.serviceGrid}`}>
            <div className={styles.serviceCopy}>
              <h2 className={styles.h2} id="service-title">
                Want the trip planned for you?
              </h2>
              <p className={styles.lead}>
                {OPERATOR_NAME} is the Tashkent travel company behind this site.
                Send your dates and group size, and we reply by email with a
                day-by-day plan, train times and prices, built on the same
                guides you read here.
              </p>
              <div className={styles.callout}>
                <SeedCluster />
                <p>
                  <strong>No payment on this site.</strong> You get the plan and
                  the prices by email first, and book only if you want to.
                </p>
              </div>
            </div>
            <div className={styles.serviceAction}>
              <Link
                className={`${styles.btn} ${styles.btnPrimary}`}
                href="/trips"
              >
                Plan my trip
              </Link>
              <p>Five questions. We reply by email.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.inner}>
          <div className={styles.footerTop}>
            <div className={styles.footerBrand}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/anor-horizontal.svg"
                alt={SITE_NAME}
                width={157}
                height={40}
                loading="lazy"
              />
              <p>
                Everything tourists and expats need to know about Uzbekistan,
                written in Tashkent and checked against the official source. Run
                by {OPERATOR_NAME}.
              </p>
            </div>
            <nav aria-label="Footer">
              <ul className={styles.footerNav}>
                {FOOTER_NAVIGATION.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href}>{item.label}</Link>
                  </li>
                ))}
                <li>
                  <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
                </li>
              </ul>
            </nav>
          </div>
          <div className={styles.footerBottom}>
            <span>
              {new Date().getFullYear()} {OPERATOR_NAME}, Tashkent.
            </span>
            <ul>
              {POLICY_NAVIGATION.map((item) => (
                <li key={item.href}>
                  <Link href={item.href}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}
