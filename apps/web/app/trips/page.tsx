import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { SITE_URL } from "@/lib/editorial-content";
import { CONTACT_EMAIL, OPERATOR_NAME } from "@/lib/site";
import { travelMonthOptions } from "@/lib/trip-inquiry";
import { InquiryForm } from "./inquiry-form";
import styles from "./trips.module.css";

const title = "Plan a trip to Uzbekistan with Kebab Travel | Uzbekistan OS";
const description =
  "Private, custom trips to Uzbekistan planned from Tashkent by the team behind Uzbekistan OS. Tell us your dates, group and interests; we reply by email with a dated plan and prices.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${SITE_URL}/trips` },
  openGraph: {
    type: "website",
    url: `${SITE_URL}/trips`,
    title,
    description,
  },
};

export default function TripsPage() {
  return (
    <div>
      <SiteHeader current="/trips" />
      <main className="page-main">
        <section className={styles.intro}>
          <h1>Plan your trip with {OPERATOR_NAME}</h1>
          <p>
            {OPERATOR_NAME} is the Tashkent travel company that publishes this
            site. We plan private trips for travellers from the US and Europe,
            using the same verified guides you read here: real train times,
            registration done properly, and hotels we have actually walked into.
          </p>
        </section>

        <section className="band" aria-labelledby="offer-title">
          <div className="band-label">
            <h2 id="offer-title">What we arrange</h2>
          </div>
          <div className={styles.offer}>
            <div>
              <h3>A route built around you</h3>
              <p>
                Day-by-day plan across Tashkent, Samarkand, Bukhara and Khiva,
                with the Fergana Valley, the mountains or the Aral Sea when they
                fit your interests and time.
              </p>
            </div>
            <div>
              <h3>Guides, drivers and tickets</h3>
              <p>
                Licensed local guides who speak your language, drivers for the
                long legs, Afrosiyob and sleeper train tickets in the right
                name, and domestic flights when they save a day.
              </p>
            </div>
            <div>
              <h3>Stays and the paperwork</h3>
              <p>
                Hotels and guesthouses chosen for location and reliability, with
                your stay registration handled, and one person in Tashkent you
                can reach while you travel.
              </p>
            </div>
          </div>
        </section>

        <section className="band" aria-labelledby="how-title">
          <div className="band-label">
            <h2 id="how-title">How it works</h2>
          </div>
          <ol className={styles.steps}>
            <li>
              <div>
                <strong>Send the inquiry below</strong>
                <span>
                  Month, nights, travellers, interests and comfort level. It
                  takes about five minutes.
                </span>
              </div>
            </li>
            <li>
              <div>
                <strong>We reply by email</strong>
                <span>
                  Usually with a few questions first, then a dated plan with
                  prices and what is included.
                </span>
              </div>
            </li>
            <li>
              <div>
                <strong>You decide; we arrange</strong>
                <span>
                  Nothing is booked and no payment is taken on this site. Terms,
                  deposits and cancellation are agreed by email before anything
                  is confirmed.
                </span>
              </div>
            </li>
          </ol>
        </section>

        <section className="band" aria-labelledby="honest-title">
          <div className="band-label">
            <h2 id="honest-title">Before you write</h2>
          </div>
          <div className={styles.honest}>
            <p>
              Prices depend on the season, the hotels you choose and the size of
              your group, so we quote per trip rather than publishing a list.
              The budget band in the form is enough for a first plan.
            </p>
            <p>
              If you would rather travel independently, you do not need us. The{" "}
              <Link href="/travel">travel guides</Link> cover trains, money,
              registration and routes in full, and they are free.
            </p>
            <p>
              Prefer plain email? Write to{" "}
              <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> with the
              same details.
            </p>
          </div>
        </section>

        <section className="band" id="inquiry" aria-labelledby="inquiry-title">
          <div className="band-label">
            <h2 id="inquiry-title">Tell us about your trip</h2>
            <p>
              Only {OPERATOR_NAME} sees this. We do not add you to a mailing
              list.
            </p>
          </div>
          <InquiryForm months={travelMonthOptions()} sourcePath="/trips" />
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
