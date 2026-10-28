import type { Metadata } from "next";
import Link from "next/link";
import { AnorMosaic } from "@/components/brand/anor-mosaic";
import { GuideIndex, type IndexGroup } from "@/components/brand/guide-index";
import { RevealOnView } from "@/components/brand/reveal-on-view";
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
import { PHOTO_LIST, PHOTOS, type Photo } from "@/lib/photos";
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

const NAV = [
  { href: "/travel", label: "Travel guides", section: "transport" },
  { href: "/living", label: "Living", section: "living" },
  { href: "/about", label: "About", section: "planning" },
] as const;

const ROUTE: { city: string; days: string; copy: string; photo: Photo }[] = [
  {
    city: "Tashkent",
    days: "1 to 2 days",
    copy: "The capital and almost every arrival point. Chorsu bazaar, a metro worth riding for its stations, and the trains west.",
    photo: PHOTOS.chorsuBazaarTashkent,
  },
  {
    city: "Samarkand",
    days: "2 days",
    copy: "Registan, Shah-i-Zinda and Gur-e-Amir. Two hours from Tashkent on the Afrosiyob.",
    photo: PHOTOS.samarkandRegistanNight,
  },
  {
    city: "Bukhara",
    days: "2 days",
    copy: "A walkable old town of madrasas, trading domes and the Kalon minaret. The best evenings on the route.",
    photo: PHOTOS.bukharaKalonMinaretDusk,
  },
  {
    city: "Khiva",
    days: "1 to 2 days",
    copy: "Itchan Kala, a walled city you can cross in fifteen minutes. The far end of the classic journey.",
    photo: PHOTOS.khivaKonyaArkNight,
  },
];

const MORE: { title: string; copy: string; photo: Photo }[] = [
  {
    title: "The Aral Sea and Nukus",
    copy: "The ship graveyard at Moynaq and the Savitsky museum, a long day north of Khiva.",
    photo: PHOTOS.moynaqShipGraveyard,
  },
  {
    title: "A night in the Kyzylkum",
    copy: "Yurt camps between Bukhara and Nukus, with Aydarkul lake for the morning.",
    photo: PHOTOS.kyzylkumYurtsNight,
  },
  {
    title: "The mountains above Tashkent",
    copy: "Chimgan, Charvak and the Pskem valley, ninety minutes from the capital.",
    photo: PHOTOS.pskemRiverMorning,
  },
];

function secureUrl(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

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

function toIndexGroup(group: BrandSectionGroup): IndexGroup {
  const guides = group.posts.map((post) => ({
    slug: post.slug,
    href: `/blog/${post.slug}`,
    title: shortTitle(post.title),
    verified: formatVerifiedDate(post.updated_at),
    verifiedAt: post.updated_at,
    image: secureUrl(post.hero_image_url),
    alt: post.hero_image_alt ?? "",
  }));
  return {
    id: group.section.id,
    title: group.section.title,
    description: group.section.description,
    href: group.section.href,
    count: countLabel(group),
    guides,
  };
}

function Credit({ photo }: { photo: Photo }) {
  return (
    <span className={styles.credit}>
      {photo.caption}. Photo {photo.credit.author}, {photo.credit.license}
    </span>
  );
}

export default async function BrandPreview() {
  const guides = await loadGuides();
  const groups = groupBySection(guides).map(toIndexGroup);
  const livingGroup = groups.find((group) => group.id === "living");
  if (livingGroup && livingGroup.guides.length === 0) {
    livingGroup.guides = LIVING_DOMAINS.map((domain) => ({
      slug: domain.slug,
      href: `/living#${domain.slug}`,
      title: domain.title,
      verified: "",
      verifiedAt: "",
      image: null,
      alt: "",
    }));
  }
  const latest = [...guides]
    .sort((a, b) => b.published_at.localeCompare(a.published_at))
    .slice(0, 6);
  const verifiedAt = latestVerification(guides);
  const hero = PHOTOS.bukharaPoiKalyanDusk;
  const service = PHOTOS.barsakelmesSunset;

  return (
    <div className={styles.page}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>

      <section className={styles.hero} aria-labelledby="hero-title">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className={styles.heroImage}
          src={hero.src}
          alt={hero.alt}
          width={hero.width}
          height={hero.height}
          fetchPriority="high"
        />
        <div className={styles.heroShade} aria-hidden="true" />

        <header className={styles.header}>
          <div className={styles.inner}>
            <Link
              className={styles.logo}
              href="/preview"
              aria-label={`${SITE_NAME} home`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/anor-mono-white-horizontal.svg"
                alt=""
                width={157}
                height={40}
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
              className={`${styles.btn} ${styles.btnOutlineLight} ${styles.headerCta}`}
              href="/trips"
            >
              Plan my trip
            </Link>
          </div>
        </header>

        <div className={`${styles.inner} ${styles.heroBody}`}>
          <div className={styles.heroCopy}>
            <h1 className={styles.heroTitle} id="hero-title">
              Everything you need to know about Uzbekistan.
            </h1>
            <p className={styles.deck}>
              Visas, money, trains, where to stay and how to live here, written
              by a team in Tashkent and checked against the official source.
            </p>
            <div className={styles.actions}>
              <Link
                className={`${styles.btn} ${styles.btnPrimary}`}
                href={FIRST_TRIP_GUIDE}
              >
                Start with the first-trip guide
              </Link>
              <Link
                className={`${styles.btn} ${styles.btnGhostLight}`}
                href="/about#methodology"
              >
                How we check facts
              </Link>
            </div>
          </div>
          <div className={styles.heroFoot}>
            <p className={styles.dateline} data-section="living">
              <i className={styles.tile} aria-hidden="true" />
              {verifiedAt ? (
                <span>
                  Last checked{" "}
                  <time dateTime={verifiedAt}>
                    {formatVerifiedDate(verifiedAt)}
                  </time>
                  . {guides.length} guides, each with its official source.
                </span>
              ) : (
                <span>Every guide shows the date it was last checked.</span>
              )}
            </p>
            <Credit photo={hero} />
          </div>
        </div>
      </section>

      <main id="main">
        <section className={styles.indexSection} aria-labelledby="index-title">
          <div className={styles.inner}>
            <div className={styles.sectionHead}>
              <h2 className={styles.h2} id="index-title">
                Guides by section
              </h2>
              <p className={styles.sectionNote}>
                Every guide names its official source and the day we checked it.
              </p>
            </div>
            <GuideIndex groups={groups} />
          </div>
        </section>

        <TileRule section="transport" />

        <section className={styles.route} aria-labelledby="route-title">
          <div className={styles.inner}>
            <div className={styles.sectionHead}>
              <h2 className={styles.h2} id="route-title">
                The classic route, west from Tashkent
              </h2>
              <p className={styles.sectionNote}>
                Seven to ten days covers it without rushing. The high-speed
                train does the long middle.
              </p>
            </div>
          </div>
          <ol className={styles.strip}>
            {ROUTE.map((stop, index) => (
              <li className={styles.stop} key={stop.city}>
                <figure>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={stop.photo.src}
                    alt={stop.photo.alt}
                    width={stop.photo.width}
                    height={stop.photo.height}
                    loading="lazy"
                    decoding="async"
                  />
                  <figcaption>
                    <span className={styles.stopIndex}>{index + 1}</span>
                    <strong>{stop.city}</strong>
                    <span className={styles.stopDays}>{stop.days}</span>
                    <p>{stop.copy}</p>
                    <Credit photo={stop.photo} />
                  </figcaption>
                </figure>
              </li>
            ))}
          </ol>
          <div className={`${styles.inner} ${styles.actions}`}>
            <Link
              className={`${styles.btn} ${styles.btnSecondary}`}
              href={FIRST_TRIP_GUIDE}
            >
              Read the seven-day route
            </Link>
            <Link
              className={`${styles.btn} ${styles.btnGhost}`}
              href="/blog/where-to-stay-in-uzbekistan"
            >
              Where to stay
            </Link>
          </div>
        </section>

        <section className={styles.more} aria-labelledby="more-title">
          <div className={styles.inner}>
            <div className={styles.sectionHead}>
              <h2 className={styles.h2} id="more-title">
                With more time
              </h2>
              <p className={styles.sectionNote}>
                Three detours that reward a longer trip.
              </p>
            </div>
            <ul className={styles.wall}>
              {MORE.map((item) => (
                <li key={item.title}>
                  <Link href="/travel#where-to-go" className={styles.wallItem}>
                    <span className={styles.frame}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={item.photo.src}
                        alt={item.photo.alt}
                        width={item.photo.width}
                        height={item.photo.height}
                        loading="lazy"
                        decoding="async"
                      />
                    </span>
                    <strong>{item.title}</strong>
                    <p>{item.copy}</p>
                    <Credit photo={item.photo} />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <TileRule section="money" />

        <section className={styles.latest} aria-labelledby="latest-title">
          <div className={styles.inner}>
            <div className={styles.sectionHead}>
              <h2 className={styles.h2} id="latest-title">
                Latest guides
              </h2>
              <Link className={styles.more2} href="/blog">
                All guides
              </Link>
            </div>
            {latest.length ? (
              <ul className={styles.cards}>
                {latest.map((post) => {
                  const section = sectionForPost(post);
                  const image = secureUrl(post.hero_image_url);
                  return (
                    <li key={post.id}>
                      <Link
                        className={styles.card}
                        data-section={section.id}
                        href={`/blog/${post.slug}`}
                      >
                        <span className={styles.frame}>
                          {image ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={image}
                              alt={post.hero_image_alt ?? ""}
                              width={1600}
                              height={1200}
                              loading="lazy"
                              decoding="async"
                            />
                          ) : null}
                        </span>
                        <span className={styles.tag}>
                          <i className={styles.tile} aria-hidden="true" />
                          {section.title}
                        </span>
                        <h3>{post.title}</h3>
                        <p className={styles.meta}>
                          Last checked{" "}
                          <time dateTime={post.updated_at}>
                            {formatVerifiedDate(post.updated_at)}
                          </time>
                        </p>
                      </Link>
                    </li>
                  );
                })}
              </ul>
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
                guides you read here. No payment on this site.
              </p>
              <div className={styles.actions}>
                <Link
                  className={`${styles.btn} ${styles.btnPrimary}`}
                  href="/trips"
                >
                  Plan my trip
                </Link>
                <span className={styles.serviceNote}>
                  Five questions. We reply by email.
                </span>
              </div>
            </div>
            <figure className={styles.servicePhoto}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={service.src}
                alt={service.alt}
                width={service.width}
                height={service.height}
                loading="lazy"
                decoding="async"
              />
              <figcaption>
                <Credit photo={service} />
              </figcaption>
            </figure>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.inner}>
          <div className={styles.footerTop}>
            <RevealOnView className={styles.footerMark}>
              <AnorMosaic />
            </RevealOnView>
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
          <div className={styles.colophon}>
            <p>
              Photographs on this page: guide photographs from the Uzbekistan OS
              library;{" "}
              {PHOTO_LIST.map((photo, index) => (
                <span key={photo.src}>
                  {index > 0 ? "; " : ""}
                  <a href={photo.credit.source} rel="license noreferrer">
                    {photo.caption}
                  </a>{" "}
                  by {photo.credit.author} ({photo.credit.license})
                </span>
              ))}
              .
            </p>
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
