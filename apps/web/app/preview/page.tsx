import type { Metadata } from "next";
import Link from "next/link";
import { formatVerifiedDate } from "@/components/site/guide-list";
import {
  listPublishedPosts,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import {
  groupTravelGuides,
  latestVerification,
  TRAVEL_CLUSTERS,
} from "@/lib/guide-clusters";
import {
  CONTACT_EMAIL,
  OPERATOR_CITY,
  OPERATOR_NAME,
  POLICY_NAVIGATION,
  PRIMARY_NAVIGATION,
  SITE_NAME,
} from "@/lib/site";
import styles from "./preview.module.css";

export const metadata: Metadata = {
  title: "Editorial preview | Uzbekistan OS",
  robots: { index: false, follow: false },
};

const FIRST_TRIP_GUIDE = "/blog/visiting-uzbekistan-first-time";
const WHERE_TO_STAY_GUIDE = "/blog/where-to-stay-in-uzbekistan";

const route = [
  {
    city: "Tashkent",
    days: "One to two days",
    copy: "The capital and almost every arrival point. Wide boulevards, the Chorsu bazaar, a metro worth riding for its stations, and the trains west.",
  },
  {
    city: "Samarkand",
    days: "Two days",
    copy: "Registan, Shah-i-Zinda and Gur-e-Amir. Two hours from Tashkent on the Afrosiyob.",
  },
  {
    city: "Bukhara",
    days: "Two days",
    copy: "A walkable old town of madrasas, trading domes and the Kalon minaret. The best evenings on the route.",
  },
  {
    city: "Khiva",
    days: "One to two days",
    copy: "Itchan Kala, a walled city you can cross in fifteen minutes. The far end of the classic journey.",
  },
];

function imageUrl(value: string | null) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

async function loadGuides(): Promise<PublishedPostSummary[]> {
  try {
    return await listPublishedPosts({ language: "en", limit: 100 });
  } catch {
    return [];
  }
}

export default async function EditorialPreview() {
  const guides = await loadGuides();
  const clusters = groupTravelGuides(guides);
  const planning = clusters
    .filter(
      (group) => group.id === "before-you-go" || group.id === "getting-around",
    )
    .flatMap((group) => group.posts)
    .slice(0, 7);
  const latest = [...guides]
    .sort((a, b) => b.published_at.localeCompare(a.published_at))
    .slice(0, 3);
  const verifiedAt = latestVerification(guides);
  const today = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Tashkent",
  }).format(new Date());
  const counts = new Map(
    clusters.map((group) => [group.id, group.posts.length]),
  );

  return (
    <div className={styles.page}>
      <div className={styles.dateline}>
        <div className={styles.inner}>
          <span>
            {OPERATOR_CITY}, {today}
          </span>
          <span>
            {verifiedAt
              ? `Guides last verified ${formatVerifiedDate(verifiedAt)}`
              : "Every guide shows its verification date"}
          </span>
        </div>
      </div>

      <header className={styles.masthead}>
        <div className={styles.inner}>
          <Link
            className={styles.brand}
            href="/preview"
            aria-label={`${SITE_NAME} home`}
          >
            <strong>{SITE_NAME}</strong>
            <small>by {OPERATOR_NAME}</small>
          </Link>
          <nav className={styles.nav} aria-label="Main navigation">
            {PRIMARY_NAVIGATION.filter((item) => !item.emphasis).map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <Link className={`${styles.btn} ${styles.mastheadCta}`} href="/trips">
            Plan my trip
          </Link>
        </div>
      </header>

      <main>
        <section className={styles.cover} aria-labelledby="cover-title">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className={styles.coverImage}
            src="/landing/hero-background.avif"
            alt="Tashkent skyline at dusk"
            width={1600}
            height={1000}
            fetchPriority="high"
          />
          <div className={styles.coverShade} aria-hidden="true" />
          <span className={styles.coverCredit}>Tashkent at dusk</span>
          <div className={`${styles.inner} ${styles.coverInner}`}>
            <div>
              <h1 className={styles.coverTitle} id="cover-title">
                Uzbekistan, planned on <em>facts</em> that are checked, dated
                and sourced.
              </h1>
              <p className={styles.coverDeck}>
                Visa rules, registration, trains, money, safety and routes for
                travellers from the US and Europe, written by a team in Tashkent
                and checked against the official source.
              </p>
              <div className={styles.coverActions}>
                <Link
                  className={`${styles.btn} ${styles.btnFilled}`}
                  href={FIRST_TRIP_GUIDE}
                >
                  Start with the first-trip guide
                </Link>
                <Link
                  className={`${styles.btn} ${styles.btnGhostLight}`}
                  href="/travel"
                >
                  All travel guides
                </Link>
              </div>
            </div>
            <aside className={styles.coverAside} aria-label="Verification">
              <span>Last verified</span>
              <strong>
                {verifiedAt ? formatVerifiedDate(verifiedAt) : "On every guide"}
              </strong>
              <p>
                Each guide names the official page behind every rule and the day
                we checked it. Rules change; the date tells you how fresh the
                page is.
              </p>
            </aside>
          </div>
        </section>

        <section className={styles.contents} aria-labelledby="contents-title">
          <div className={styles.inner}>
            <div>
              <h2 className={styles.sectionTitle} id="contents-title">
                In this <em>issue</em>
              </h2>
              <p className={styles.sectionIntro}>
                The guides are grouped the way a trip unfolds: what to settle
                before you fly, how to move once you land, where to go, and what
                to eat when you get there.
              </p>
              <ul className={styles.index}>
                {TRAVEL_CLUSTERS.map((cluster) => (
                  <li key={cluster.id}>
                    <Link href={`/travel#${cluster.id}`}>
                      <span>{cluster.title}</span>
                      <span>
                        {counts.get(cluster.id) ?? 0}{" "}
                        {(counts.get(cluster.id) ?? 0) === 1
                          ? "guide"
                          : "guides"}
                      </span>
                    </Link>
                  </li>
                ))}
                <li>
                  <Link href="/living">
                    <span>Living in Uzbekistan</span>
                    <span>second section</span>
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              {planning.length ? (
                <ul className={styles.guideList} aria-label="Before you go">
                  {planning.map((post) => (
                    <li key={post.id}>
                      <Link href={`/blog/${post.slug}`}>
                        <h3>{post.title}</h3>
                        <span className={styles.verified}>
                          Verified{" "}
                          <time dateTime={post.updated_at}>
                            {formatVerifiedDate(post.updated_at)}
                          </time>
                        </span>
                        <p>{post.summary}</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.empty}>
                  The guide library is loading. Browse{" "}
                  <Link href="/blog">all published guides</Link>.
                </p>
              )}
            </div>
          </div>
        </section>

        <section className={styles.feature} aria-labelledby="route-title">
          <div className={styles.inner}>
            <div>
              <h2 className={styles.sectionTitle} id="route-title">
                The classic route, <em>west along the Silk Road</em>
              </h2>
              <p className={styles.sectionIntro}>
                Most first trips follow one line from the capital to the desert.
                Seven to ten days covers it without rushing; the high-speed
                train does the long middle.
              </p>
              <p className={styles.featureNote}>
                With more time, add the Fergana Valley for ceramics and silk, or
                Nukus and the Aral Sea for the Savitsky museum and the ship
                graveyard at Moynaq.
              </p>
              <div className={styles.featureActions}>
                <Link
                  className={`${styles.btn} ${styles.btnFilled}`}
                  href={FIRST_TRIP_GUIDE}
                >
                  Read the seven-day route
                </Link>
                <Link className={styles.btn} href={WHERE_TO_STAY_GUIDE}>
                  Where to stay
                </Link>
              </div>
            </div>
            <ol className={styles.route}>
              {route.map((stop) => (
                <li key={stop.city}>
                  <h3>
                    {stop.city}
                    <em>{stop.days}</em>
                  </h3>
                  <p>{stop.copy}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className={styles.latest} aria-labelledby="latest-title">
          <div className={styles.inner}>
            <div className={styles.latestHead}>
              <h2 className={styles.sectionTitle} id="latest-title">
                Latest <em>guides</em>
              </h2>
              <Link className={styles.sectionLink} href="/blog">
                All guides
              </Link>
            </div>
            {latest.length ? (
              <div className={styles.grid}>
                {latest.map((post) => {
                  const image = imageUrl(post.hero_image_url);
                  return (
                    <Link
                      className={styles.story}
                      href={`/blog/${post.slug}`}
                      key={post.id}
                    >
                      {image ? (
                        <div className={styles.storyImage}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={image}
                            alt={post.hero_image_alt ?? ""}
                            loading="lazy"
                            decoding="async"
                            width={1600}
                            height={1200}
                          />
                        </div>
                      ) : null}
                      <p className={styles.storyMeta}>
                        {post.domain_slug === "tourism" ? "Travel" : "Living"},
                        verified {formatVerifiedDate(post.updated_at)}
                      </p>
                      <h3>{post.title}</h3>
                      <p>{post.summary}</p>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <p className={styles.empty}>
                Published guides appear here. See{" "}
                <Link href="/blog">all guides</Link>.
              </p>
            )}
          </div>
        </section>

        <section className={styles.service} aria-labelledby="service-title">
          <div className={styles.inner}>
            <div>
              <h2 className={styles.sectionTitle} id="service-title">
                Rather have it <em>arranged?</em>
              </h2>
              <p className={styles.sectionIntro}>
                {OPERATOR_NAME} is the Tashkent travel company behind this site.
                Tell us your dates, your group and what you care about, and we
                reply by email with a dated plan, prices, and the trains and
                stays we would book.
              </p>
              <div className={styles.serviceActions}>
                <Link
                  className={`${styles.btn} ${styles.btnClay}`}
                  href="/trips"
                >
                  Plan my trip
                </Link>
                <p>Email inquiry. No payment is taken on this site.</p>
              </div>
            </div>
            <ol className={styles.serviceSteps}>
              <li>
                <div>
                  <strong>Tell us about the trip</strong>
                  <span>
                    Month, nights, travellers, interests and comfort level. Five
                    minutes.
                  </span>
                </div>
              </li>
              <li>
                <div>
                  <strong>Get a dated plan with prices</strong>
                  <span>
                    A day-by-day route with train times, stays and what is
                    included, built on the same guides you read here.
                  </span>
                </div>
              </li>
              <li>
                <div>
                  <strong>Decide, then we arrange it</strong>
                  <span>
                    Guides, drivers, tickets and hotels, with one person in
                    Tashkent you can reach while you travel.
                  </span>
                </div>
              </li>
            </ol>
          </div>
        </section>

        <section className={styles.living} aria-labelledby="living-title">
          <div className={styles.inner}>
            <div>
              <h2 className={styles.sectionTitle} id="living-title">
                Staying <em>longer?</em>
              </h2>
              <p className={styles.sectionIntro}>
                The same verified approach applies to residence, work, business
                and healthcare. These guides began the site and continue as its
                second section.
              </p>
              <Link className={styles.sectionLink} href="/living">
                Living in Uzbekistan guides
              </Link>
            </div>
            <ul className={styles.topics}>
              <li>Registration and extending a stay</li>
              <li>Temporary residence and work permits</li>
              <li>Starting a company and paying tax</li>
              <li>Bank accounts, PINFL and renting</li>
              <li>Healthcare and insurance</li>
              <li>Leaving with the paperwork in order</li>
            </ul>
          </div>
        </section>

        <section className={styles.verify} aria-labelledby="verify-title">
          <div className={styles.inner}>
            <div>
              <h2 className={styles.sectionTitle} id="verify-title">
                How we <em>verify</em>
              </h2>
              <Link className={styles.sectionLink} href="/about#methodology">
                Our methodology
              </Link>
            </div>
            <div>
              <h3>Dated and sourced</h3>
              <p>
                Every rule, price and timetable links to the official page we
                checked and shows the date we checked it. If we could not
                confirm something, the guide says so.
              </p>
            </div>
            <div>
              <h3>Independent of the trips we sell</h3>
              <p>
                Guides do not change because of what {OPERATOR_NAME} offers. The
                trip service appears only in clearly labelled places, never
                inside the advice.
              </p>
            </div>
            <div>
              <h3>Written from Tashkent</h3>
              <p>
                The authors live and work in Uzbekistan and check rules at the
                airport, the station and the bank, not only on a website.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.colophon}>
        <div className={styles.inner}>
          <p className={styles.colophonBrand}>
            {SITE_NAME}
            <small>
              by {OPERATOR_NAME}, {OPERATOR_CITY}
            </small>
          </p>
          <div className={styles.colophonGrid}>
            <div>
              <p>
                {SITE_NAME} is published by {OPERATOR_NAME}, a travel company in{" "}
                {OPERATOR_CITY}. Every guide is dated and tied to the official
                source behind it. Guides are independent of the trips we plan.
              </p>
              <p style={{ marginTop: 12 }}>
                <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
              </p>
            </div>
            <nav aria-labelledby="colophon-explore">
              <h2 id="colophon-explore">Explore</h2>
              <ul>
                {PRIMARY_NAVIGATION.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href}>{item.label}</Link>
                  </li>
                ))}
                <li>
                  <Link href="/blog">All guides</Link>
                </li>
              </ul>
            </nav>
            <nav aria-labelledby="colophon-policies">
              <h2 id="colophon-policies">Policies and feeds</h2>
              <ul>
                {POLICY_NAVIGATION.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
          <div className={styles.colophonFoot}>
            <span>
              © {new Date().getUTCFullYear()} {OPERATOR_NAME}, {OPERATOR_CITY},
              Uzbekistan
            </span>
            <span>
              Guidance, not legal advice. Confirm rules with the official source
              before you travel.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
