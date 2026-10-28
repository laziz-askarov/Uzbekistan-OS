import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";
import LatestBlogs from "@/components/editorial/latest-blogs";
import { GuideList, formatVerifiedDate } from "@/components/site/guide-list";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import {
  listPublishedPosts,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import { groupTravelGuides, latestVerification } from "@/lib/guide-clusters";
import { OPERATOR_NAME, SITE_TAGLINE } from "@/lib/site";
import styles from "./home.module.css";

const FIRST_TRIP_GUIDE = "/blog/visiting-uzbekistan-first-time";
const WHERE_TO_STAY_GUIDE = "/blog/where-to-stay-in-uzbekistan";

const route = [
  {
    city: "Tashkent",
    days: "1 to 2 days",
    copy: "The capital and almost every arrival point. Soviet-era boulevards, the Chorsu bazaar, the metro, and the trains onward.",
  },
  {
    city: "Samarkand",
    days: "2 days",
    copy: "Registan, Shah-i-Zinda and Gur-e-Amir. Two hours from Tashkent on the Afrosiyob high-speed train.",
  },
  {
    city: "Bukhara",
    days: "2 days",
    copy: "A walkable old town of madrasas, trading domes and the Kalon minaret. The most atmospheric evenings on the route.",
  },
  {
    city: "Khiva",
    days: "1 to 2 days",
    copy: "Itchan Kala, a walled city you can cross in fifteen minutes. The far end of the classic route.",
  },
];

function VerifiedIcon() {
  return (
    <svg viewBox="0 0 22 22" aria-hidden="true" focusable="false">
      <circle cx="11" cy="11" r="10" fill="currentColor" opacity="0.14" />
      <path
        d="M6.5 11.3l3 3 6-6.4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

async function loadGuides(): Promise<PublishedPostSummary[]> {
  try {
    return await listPublishedPosts({ language: "en", limit: 100 });
  } catch {
    // The editorial API deploys separately; the homepage must stay useful without it.
    return [];
  }
}

export default async function HomePage() {
  const guides = await loadGuides();
  const clusters = groupTravelGuides(guides);
  const planning = clusters
    .filter(
      (group) => group.id === "before-you-go" || group.id === "getting-around",
    )
    .flatMap((group) => group.posts)
    .slice(0, 8);
  const verifiedAt = latestVerification(guides);

  return (
    <div>
      <SiteHeader current="/" />
      <main className="page-main" id="top">
        <section className={styles.hero} id="hero" aria-labelledby="hero-title">
          <div className={styles.heroCopy}>
            <p className={styles.tagline}>{SITE_TAGLINE}</p>
            <h1 id="hero-title">
              Plan Uzbekistan with facts that are checked, dated and sourced.
            </h1>
            <p className={styles.lede}>
              Visa rules, registration, trains, money, SIM cards, safety and
              itineraries for travellers from the US and Europe, written by a
              team in Tashkent. Every guide shows when we last verified it and
              which official source says so.
            </p>
            <div className={styles.heroActions}>
              <Link className="btn btn-primary" href={FIRST_TRIP_GUIDE}>
                Start with the first-trip guide
              </Link>
              <Link className="btn btn-quiet" href="/trips">
                Plan my trip with {OPERATOR_NAME}
              </Link>
            </div>
          </div>
          <figure className={styles.figure}>
            <Image
              alt="Tashkent skyline at sunset"
              fill
              priority
              sizes="(max-width: 960px) 100vw, 480px"
              src="/landing/hero-background.avif"
            />
            <aside
              className={styles.verifiedCard}
              aria-label="How this site is verified"
            >
              <span className={styles.verifiedHead}>
                <VerifiedIcon />
                Last verified
              </span>
              <time
                className={styles.verifiedDate}
                dateTime={verifiedAt ?? undefined}
              >
                {verifiedAt ? formatVerifiedDate(verifiedAt) : "On every guide"}
              </time>
              <p>
                Each guide lists the official source behind every rule and the
                date we checked it. Rules change; the date tells you how fresh
                the page is.
              </p>
            </aside>
          </figure>
        </section>

        <section
          className="band"
          id="before-you-go"
          aria-labelledby="before-you-go-title"
        >
          <div className="band-label">
            <h2 id="before-you-go-title">Before you go</h2>
            <p>
              Entry rules, registration, money, phones and safety, each checked
              against the official source. Start here if this is your first
              trip.
            </p>
            <Link href="/travel">All travel guides</Link>
          </div>
          <div>
            {planning.length ? (
              <GuideList posts={planning} labelledBy="before-you-go-title" />
            ) : (
              <p className={styles.fallback}>
                The guide library is loading. Browse{" "}
                <Link href="/travel">travel guides</Link> or{" "}
                <Link href="/blog">all published guides</Link>.
              </p>
            )}
          </div>
        </section>

        <section
          className="band"
          id="where-to-go"
          aria-labelledby="where-to-go-title"
        >
          <div className="band-label">
            <h2 id="where-to-go-title">Where to go</h2>
            <p>
              Most first trips follow one route west along the old Silk Road.
              Seven to ten days covers it without rushing.
            </p>
          </div>
          <div>
            <ol className={styles.route}>
              {route.map((stop) => (
                <li className={styles.stop} key={stop.city}>
                  <h3>{stop.city}</h3>
                  <span className={styles.stopDays}>{stop.days}</span>
                  <p>{stop.copy}</p>
                </li>
              ))}
            </ol>
            <p className={styles.routeNote}>
              With more time, add the Fergana Valley for ceramics and silk, or
              Nukus and the Aral Sea for the Savitsky museum and the ship
              graveyard at Moynaq.
            </p>
            <div className={styles.routeActions}>
              <Link className="btn btn-primary" href={FIRST_TRIP_GUIDE}>
                Read the seven-day route
              </Link>
              <Link className="btn btn-quiet" href={WHERE_TO_STAY_GUIDE}>
                Where to stay in each city
              </Link>
            </div>
          </div>
        </section>

        <Suspense fallback={null}>
          <LatestBlogs />
        </Suspense>

        <section className="band" id="living" aria-labelledby="living-title">
          <div className="band-label">
            <h2 id="living-title">Living in Uzbekistan</h2>
            <p>
              Staying longer than a holiday? The same verified approach applies
              to residence, work, business and healthcare.
            </p>
            <Link href="/living">Living in Uzbekistan guides</Link>
          </div>
          <div className={styles.livingBody}>
            <p>
              Uzbekistan OS began as a reference for the official procedures
              that foreigners meet after arrival. Those guides continue here,
              written the same way: dated, sourced and reviewed before
              publication.
            </p>
            <ul className={styles.livingTopics}>
              <li>Registration and extending a stay</li>
              <li>Temporary residence and work permits</li>
              <li>Starting a company and paying tax</li>
              <li>Bank accounts, PINFL and renting</li>
              <li>Healthcare and insurance</li>
              <li>Leaving with the paperwork in order</li>
            </ul>
          </div>
        </section>

        <section
          className={styles.service}
          id="plan-a-trip"
          aria-labelledby="plan-a-trip-title"
        >
          <div>
            <h2 id="plan-a-trip-title">
              Want it arranged? {OPERATOR_NAME} plans the trip.
            </h2>
            <p>
              {OPERATOR_NAME} is the Tashkent travel company behind this site.
              Tell us your dates, your group and what you care about, and we
              reply by email with a plan, prices and the trains and stays we
              would book.
            </p>
            <div className={styles.serviceActions}>
              <Link className="btn btn-service" href="/trips">
                Plan my trip
              </Link>
              <p className={styles.serviceNote}>
                Email inquiry. No payment is taken on this site.
              </p>
            </div>
          </div>
          <ol className={styles.steps}>
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
        </section>

        <section
          className="band"
          id="how-we-verify"
          aria-labelledby="how-we-verify-title"
        >
          <div className="band-label">
            <h2 id="how-we-verify-title">How we verify</h2>
            <Link href="/about#methodology">Our methodology</Link>
          </div>
          <div className={styles.principles}>
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
                trip service appears only in clearly labelled boxes, never
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
      <SiteFooter />
    </div>
  );
}
