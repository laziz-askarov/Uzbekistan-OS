import Image from "next/image";
import type { ReactNode } from "react";

const OFFICIAL_E_VISA_URL = "https://www.e-visa.gov.uz/";
const OFFICIAL_VISA_URL =
  "https://gov.uz/en/mfa/activity_page/o-zbekiston-respublikasi-vizasi";
const FOREIGNER_SERVICES_URL = "https://my.gov.uz/kaa/for-foreigners";

const features = [
  {
    title: "Start with your passport",
    description:
      "Your nationality determines whether you can enter visa-free, use an e-visa, or need a consular visa.",
    icon: "/landing/feature-official.svg",
    tone: "blue",
  },
  {
    title: "Choose the right purpose",
    description:
      "Tourism, business, work, study, family visits, treatment, and transit follow different visa tracks.",
    icon: "/landing/feature-ai.svg",
    tone: "purple",
  },
  {
    title: "Prepare the full file",
    description:
      "See the passport, photo, invitation, sponsor, enrollment, and onward-travel documents each route needs.",
    icon: "/landing/feature-time.svg",
    tone: "green",
  },
  {
    title: "Stay compliant after arrival",
    description:
      "Entry permission and local address registration are separate obligations. Most visitors must register promptly.",
    icon: "/landing/feature-private.svg",
    tone: "orange",
  },
] as const;

const personalPlanItems = [
  {
    number: "01",
    title: "Your exact visa route",
    description:
      "A recommendation based on nationality, passport type, travel purpose, intended stay, and sponsor situation.",
  },
  {
    number: "02",
    title: "Complete document checklist",
    description:
      "Every required document, format, translation, invitation, photograph, and supporting record in one place.",
  },
  {
    number: "03",
    title: "Application process",
    description:
      "A clear sequence showing who applies, where to submit, what happens next, and what to bring to the border.",
  },
  {
    number: "04",
    title: "Processing time",
    description:
      "The expected government and sponsor stages, with enough lead time to plan travel responsibly.",
  },
  {
    number: "05",
    title: "Fees and validity",
    description:
      "Relevant consular fees, entries, permitted stay, validity window, and renewal or extension conditions.",
  },
  {
    number: "06",
    title: "Arrival requirements",
    description:
      "Registration, accommodation evidence, deadlines, restrictions, and the next compliance step after entry.",
  },
] as const;

const routes = [
  {
    title: "Visa-free entry",
    description:
      "For eligible passports. The permitted stay is nationality-specific and begins when you cross the border.",
    image: "/landing/category-immigration.png",
    icon: "/landing/category-immigration.svg",
    tone: "immigration",
    href: "#visa-free",
  },
  {
    title: "Electronic visa",
    description:
      "An online route for eligible nationalities, with single, double, and multiple-entry options.",
    image: "/landing/category-business.png",
    icon: "/landing/category-business.svg",
    tone: "business",
    href: "#electronic-visa",
  },
  {
    title: "Business & work",
    description:
      "Business visits, accredited roles, investment, and employment each require the correct category and sponsor.",
    image: "/landing/category-employment.png",
    icon: "/landing/category-employment.svg",
    tone: "employment",
    href: "#common-visas",
  },
  {
    title: "Study & family",
    description:
      "Institution-sponsored study and host-sponsored private visits use different invitation and renewal paths.",
    image: "/landing/category-education.png",
    icon: "/landing/category-education.svg",
    tone: "education",
    href: "#common-visas",
  },
] as const;

const commonVisas = [
  {
    title: "Tourist visa · T / TG",
    summary:
      "For individual leisure travel or a tourist group of at least five people.",
    facts: [
      "Standard tourist visas are generally issued for up to one month.",
      "TG is the group tourist category; e-visas are a separate electronic route.",
      "Prepare a valid passport, completed application, passport photo, accommodation details, and itinerary when requested.",
    ],
  },
  {
    title: "Business visa · B-1 / B-2",
    summary:
      "For accredited commercial representatives or temporary business visits—not local employment.",
    facts: [
      "B-1 covers accredited representatives of foreign commercial, banking, or financial organizations.",
      "B-2 covers temporary business visitors and may be issued for up to one year.",
      "The inviting Uzbek entity normally initiates visa support. A business visa does not itself authorize local salaried work.",
    ],
  },
  {
    title: "Work visa",
    summary:
      "For foreign nationals authorized to work for an employer in Uzbekistan.",
    facts: [
      "The work route depends on authorization from the competent labor migration authority.",
      "Employer support and employment documents are required before visa issuance.",
      "Do not use a tourist or business visa as a substitute for employment authorization.",
    ],
  },
  {
    title: "Study visas · STD / A-1",
    summary:
      "For exchange study or full-period enrollment at an educational institution in Uzbekistan.",
    facts: [
      "STD covers temporary study or formal exchange programs; A-1 covers study for the academic period.",
      "The institution normally requests visa support and provides the approval or telex details.",
      "Bring proof of admission, passport and photo, and any medical or financial documents required for the length of stay.",
    ],
  },
  {
    title: "Private & family visits · PV-1 / PV-2 / VTD",
    summary:
      "For invited private visits and qualifying former citizens or family members.",
    facts: [
      "PV-1 is based on a request from an Uzbek citizen; PV-2 is based on a request from an eligible foreign resident.",
      "VTD is for qualifying people born in Uzbekistan and family members invited by relatives who are Uzbek citizens.",
      "Expect identity, kinship, host-address, invitation, and support documents. Family or visitor status does not automatically grant work rights or permanent residence.",
    ],
  },
  {
    title: "Transit visa · TRAN",
    summary:
      "For passage through Uzbekistan to a third country, generally for up to three days.",
    facts: [
      "A destination-country visa, when required, and confirmed onward travel are normally needed.",
      "Some nationalities may qualify for a separate five-day visa-free air-transit regime under specific conditions.",
      "Check the official country list and routing conditions before travel.",
    ],
  },
  {
    title: "Medical visa",
    summary:
      "For treatment in Uzbekistan at the invitation of a medical institution.",
    facts: [
      "The official catalogue provides for stays of up to three months.",
      "An invitation from the treatment or prevention institution is required.",
      "Keep treatment confirmation, accommodation, and any companion documentation with the application.",
    ],
  },
  {
    title: "Investment visa · INV",
    summary:
      "A multiple-entry route for qualifying investors and eligible family members.",
    facts: [
      "The investing enterprise applies and must document that the statutory investment threshold is met.",
      "The official category may be valid for up to three years and can allow in-country extension.",
      "Thresholds are tied to Uzbekistan’s base calculation amount and must be confirmed at the time of application.",
    ],
  },
] as const;

const visaGroups = [
  {
    title: "Diplomatic & official",
    visas: [
      [
        "D-1",
        "Diplomatic · permanent accreditation",
        "For qualifying mission staff and dependants for the accreditation period.",
      ],
      [
        "D-2",
        "Diplomatic · temporary",
        "For qualifying mission staff and dependants for up to three months.",
      ],
      [
        "DT",
        "Diplomatic tourist",
        "Tourist entry for diplomatic passport holders for up to one month.",
      ],
      [
        "Official",
        "Official or state visit",
        "For invited official delegations for the duration of the official event.",
      ],
    ],
  },
  {
    title: "Service, business & media",
    visas: [
      [
        "S-1",
        "Service · permanent accreditation",
        "For qualifying service and international-organization personnel for the accreditation period.",
      ],
      [
        "S-2",
        "Service · temporary",
        "For qualifying service personnel and dependants for up to three months.",
      ],
      [
        "S-3",
        "Service · state invitation",
        "For business trips invited by eligible state organizations, for up to one year.",
      ],
      [
        "B-1",
        "Business · accredited",
        "For accredited representatives of foreign commercial and financial organizations.",
      ],
      [
        "B-2",
        "Business · temporary",
        "For temporary representatives of business circles, for up to one year.",
      ],
      [
        "J-1",
        "Press · permanent accreditation",
        "For permanently accredited foreign media representatives and eligible dependants.",
      ],
      [
        "J-2",
        "Press · temporary accreditation",
        "For foreign media representatives for the approved accreditation period.",
      ],
    ],
  },
  {
    title: "Travel, private visits & heritage",
    visas: [
      ["T", "Tourist", "For individual tourism, for up to one month."],
      [
        "TG",
        "Group tourist",
        "For tourism groups of at least five people, for up to one month.",
      ],
      [
        "PLG",
        "Pilgrimage",
        "For cultural, historical, religious, and spiritual heritage travel, for up to two months.",
      ],
      [
        "PV-1",
        "Private visit · Uzbek citizen host",
        "For guests invited through a request from an Uzbek citizen, for up to one year.",
      ],
      [
        "PV-2",
        "Private visit · foreign resident host",
        "For guests invited by an eligible accredited and registered foreign citizen, for up to one year.",
      ],
      [
        "VTD",
        "Compatriot",
        "For qualifying Uzbekistan-born people and family members, for up to two years.",
      ],
    ],
  },
  {
    title: "Work, study & specialist",
    visas: [
      [
        "Work",
        "Employment",
        "For authorized foreign workers, for the period approved by the competent authority.",
      ],
      [
        "STD",
        "Student exchange",
        "For temporary or exchange study, for up to one year.",
      ],
      [
        "A-1",
        "Student",
        "For study at an educational institution, for up to one year.",
      ],
      [
        "A-2",
        "Teacher",
        "For qualifying foreign teaching staff, for up to one year.",
      ],
      [
        "A-3",
        "Academic",
        "For research or temporary teaching, from three months up to two years.",
      ],
      [
        "Medical",
        "Medical treatment",
        "For invited treatment at an eligible institution, for up to three months.",
      ],
    ],
  },
  {
    title: "Transport, exit & investment",
    visas: [
      [
        "C-1",
        "Aircraft or railway crew",
        "For foreign crew members, for up to one year.",
      ],
      [
        "C-2",
        "Freight driver",
        "For foreign freight-vehicle drivers, for up to one year.",
      ],
      [
        "TRAN",
        "Transit",
        "For transit through Uzbekistan, for up to three days.",
      ],
      [
        "EXIT",
        "Exit",
        "For departure after an entry visa has expired, for up to one month.",
      ],
      [
        "INV",
        "Investment",
        "A multiple-entry category for qualifying investors, valid for up to three years.",
      ],
    ],
  },
] as const;

function Arrow({ variant = "dark" }: { variant?: "dark" | "white" | "light" }) {
  return (
    <Image
      aria-hidden="true"
      alt=""
      height={18}
      src={`/landing/arrow-${variant}.svg`}
      width={18}
    />
  );
}

function ExternalLink({
  href,
  children,
  className,
}: {
  href: string;
  children: ReactNode;
  className: string;
}) {
  return (
    <a className={className} href={href} rel="noreferrer" target="_blank">
      <span>{children}</span>
      <Arrow variant={className.includes("dark") ? "light" : "dark"} />
    </a>
  );
}

export default function HomePage() {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <a
          className="landing-brand"
          href="#top"
          aria-label="Uzbekistan OS home"
        >
          Uzbekistan OS
        </a>
        <a className="pill pill-dark pill-compact" href="/signup">
          <span>Sign up</span>
          <Arrow variant="light" />
        </a>
      </header>

      <main className="landing-main" id="top">
        <section className="skyline" aria-label="Travel to Uzbekistan">
          <Image
            alt="Tashkent skyline at sunset"
            className="skyline-image"
            fill
            priority
            sizes="(max-width: 1280px) calc(100vw - 48px), 1232px"
            src="/landing/hero-background.avif"
          />
          <div className="skyline-fade" aria-hidden="true" />
        </section>

        <section className="hero-content" aria-labelledby="hero-title">
          <p className="hero-eyebrow">Uzbekistan visa guide</p>
          <h1 id="hero-title">
            <span>Find the right visa</span>
            <span>for Uzbekistan</span>
          </h1>
          <p className="hero-description">
            Create your account and get a personalized visa plan with the right
            route, complete documents, application steps, processing time, fees,
            validity, and arrival requirements.
          </p>
          <div className="hero-actions">
            <a className="pill pill-dark" href="/signup">
              <span>Create free account</span>
              <Arrow variant="white" />
            </a>
            <a className="pill pill-light" href="#personal-plan">
              <span>See what you’ll get</span>
              <Arrow />
            </a>
          </div>
          <p className="hero-note">
            Rules depend on nationality, passport type, purpose, and length of
            stay. Always confirm your route on the official government portal
            before booking.
          </p>
        </section>

        <section
          className="personal-plan"
          id="personal-plan"
          aria-labelledby="personal-plan-title"
        >
          <div className="personal-plan-intro">
            <p className="section-kicker">Your visa workspace</p>
            <h2 id="personal-plan-title">
              One account. One complete plan for your trip.
            </h2>
            <p>
              Tell us why you are traveling and the details that affect your
              eligibility. Uzbekistan OS turns them into a personalized,
              evidence-backed path you can follow from research to arrival.
            </p>
            <a className="pill pill-dark" href="/signup">
              <span>Sign up and build my plan</span>
              <Arrow variant="white" />
            </a>
          </div>
          <div className="personal-plan-grid">
            {personalPlanItems.map((item) => (
              <article className="personal-plan-item" key={item.number}>
                <span>{item.number}</span>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          className="features"
          aria-label="How Uzbekistan OS helps with visas"
        >
          {features.map((feature) => (
            <article className="feature" key={feature.title}>
              <span className={`feature-icon feature-icon-${feature.tone}`}>
                <Image alt="" height={28} src={feature.icon} width={28} />
              </span>
              <h2>{feature.title}</h2>
              <p>{feature.description}</p>
            </article>
          ))}
        </section>

        <section
          className="categories"
          id="visa-routes"
          aria-labelledby="routes-title"
        >
          <div className="categories-heading">
            <p className="section-kicker">Start here</p>
            <h2 id="routes-title">Choose your visa route</h2>
            <p>
              Begin with the path that matches your passport and purpose of
              travel.
            </p>
          </div>
          <div className="category-grid">
            {routes.map((route) => (
              <article
                className={`category-card category-${route.tone}`}
                key={route.title}
              >
                <Image
                  alt=""
                  className="category-texture"
                  fill
                  sizes="(max-width: 767px) calc(100vw - 48px), (max-width: 1023px) 45vw, 290px"
                  src={route.image}
                />
                <div className="category-content">
                  <span className="category-icon">
                    <Image alt="" height={24} src={route.icon} width={24} />
                  </span>
                  <div className="category-copy">
                    <h3>{route.title}</h3>
                    <p>{route.description}</p>
                    <a
                      className="category-link"
                      href={route.href}
                      aria-label={`Read about ${route.title}`}
                    >
                      <Arrow variant="white" />
                    </a>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="route-explainer" aria-labelledby="entry-path-title">
          <div className="section-intro">
            <p className="section-kicker">Entry pathways</p>
            <h2 id="entry-path-title">Three ways most visitors enter</h2>
            <p>
              Check them in this order. If one route does not apply to your
              passport or purpose, continue to the next.
            </p>
          </div>
          <div className="path-grid">
            <article className="path-card" id="visa-free">
              <span className="path-number">01</span>
              <p className="path-label">No advance visa</p>
              <h3>Visa-free entry</h3>
              <p>
                Eligible travelers present a valid passport at the border. Stay
                limits and special conditions vary by nationality and passport
                type.
              </p>
              <ul>
                <li>No visa application or consular fee.</li>
                <li>The stay clock begins at border entry.</li>
                <li>
                  Longer stays require the appropriate visa or residence route.
                </li>
              </ul>
              <a href={OFFICIAL_VISA_URL} rel="noreferrer" target="_blank">
                Check the official country list <Arrow />
              </a>
            </article>
            <article className="path-card" id="electronic-visa">
              <span className="path-number">02</span>
              <p className="path-label">Apply online</p>
              <h3>Electronic visa</h3>
              <p>
                The official e-visa portal checks whether your nationality is
                eligible and interrupts the application when you do not need—or
                cannot use—this route.
              </p>
              <ul>
                <li>
                  Single entry: $20; double entry: $35; multiple entry: $50.
                </li>
                <li>
                  Upload a readable passport data page and ICAO-compliant facial
                  photo.
                </li>
                <li>
                  Enter details exactly as shown in the passport and keep the
                  issued PDF with you.
                </li>
              </ul>
              <a href={OFFICIAL_E_VISA_URL} rel="noreferrer" target="_blank">
                Open the official e-visa portal <Arrow />
              </a>
            </article>
            <article className="path-card path-card-dark">
              <span className="path-number">03</span>
              <p className="path-label">Invitation or specialist route</p>
              <h3>Consular visa</h3>
              <p>
                Longer, sponsored, employment, education, family, diplomatic,
                and specialist visits generally use visa support and an Uzbek
                embassy or consulate.
              </p>
              <ul>
                <li>
                  The host, employer, institution, or inviting person starts the
                  support process when required.
                </li>
                <li>
                  Submit the approved visa support details, application,
                  passport, and photographs.
                </li>
                <li>
                  Transit applicants also show onward travel and any
                  destination-country visa.
                </li>
              </ul>
              <a href={OFFICIAL_VISA_URL} rel="noreferrer" target="_blank">
                Read official consular requirements <Arrow variant="light" />
              </a>
            </article>
          </div>
        </section>

        <section
          className="common-visas"
          id="common-visas"
          aria-labelledby="common-title"
        >
          <div className="section-intro section-intro-split">
            <div>
              <p className="section-kicker">Detailed guides</p>
              <h2 id="common-title">The visas travelers ask about most</h2>
            </div>
            <p>
              Open a guide to see who it is for, what usually supports the
              application, and the restriction most likely to affect the trip.
            </p>
          </div>
          <div className="visa-accordion-grid">
            {commonVisas.map((visa, index) => (
              <details
                className="visa-detail"
                key={visa.title}
                open={index === 0}
              >
                <summary>
                  <span>
                    <small>{String(index + 1).padStart(2, "0")}</small>
                    <strong>{visa.title}</strong>
                    <em>{visa.summary}</em>
                  </span>
                  <span className="detail-toggle" aria-hidden="true">
                    +
                  </span>
                </summary>
                <ul>
                  {visa.facts.map((fact) => (
                    <li key={fact}>{fact}</li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </section>

        <section
          className="visa-catalogue"
          id="visa-catalogue"
          aria-labelledby="catalogue-title"
        >
          <div className="section-intro section-intro-split">
            <div>
              <p className="section-kicker">Complete catalogue</p>
              <h2 id="catalogue-title">Every non-electronic visa category</h2>
            </div>
            <p>
              This catalogue follows the Ministry of Foreign Affairs list.
              Category codes and permitted periods describe the route—not an
              automatic right to issuance or entry.
            </p>
          </div>
          <div className="catalogue-groups">
            {visaGroups.map((group) => (
              <section
                className="catalogue-group"
                key={group.title}
                aria-labelledby={`group-${group.title.replaceAll(" ", "-")}`}
              >
                <h3 id={`group-${group.title.replaceAll(" ", "-")}`}>
                  {group.title}
                </h3>
                <div className="catalogue-list">
                  {group.visas.map(([code, name, description]) => (
                    <article className="catalogue-item" key={`${code}-${name}`}>
                      <span>{code}</span>
                      <div>
                        <h4>{name}</h4>
                        <p>{description}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </section>

        <section className="travel-checklist" aria-labelledby="checklist-title">
          <div className="checklist-heading">
            <p className="section-kicker">Before you submit</p>
            <h2 id="checklist-title">A visa-ready file starts here</h2>
            <p>
              Individual categories can add sponsor-specific evidence, but these
              checks prevent the most common application problems.
            </p>
          </div>
          <ol className="checklist-steps">
            <li>
              <span>1</span>
              <div>
                <h3>Confirm passport validity</h3>
                <p>
                  The official baseline is at least three months beyond the visa
                  period; airlines or routes may apply a six-month
                  travel-document standard. Keep blank pages available.
                </p>
              </div>
            </li>
            <li>
              <span>2</span>
              <div>
                <h3>Match the purpose exactly</h3>
                <p>
                  Tourism, meetings, paid work, study, family visits, and
                  medical treatment are not interchangeable purposes.
                </p>
              </div>
            </li>
            <li>
              <span>3</span>
              <div>
                <h3>Secure invitation support</h3>
                <p>
                  For sponsored routes, wait for the inviting organization,
                  university, employer, clinic, or host to complete its part
                  before consular submission.
                </p>
              </div>
            </li>
            <li>
              <span>4</span>
              <div>
                <h3>Copy details without variation</h3>
                <p>
                  Your name, passport number, dates, and document images must
                  match the passport used at the border.
                </p>
              </div>
            </li>
          </ol>
        </section>

        <section className="arrival-panel" aria-labelledby="arrival-title">
          <div className="arrival-copy">
            <p className="section-kicker">After arrival</p>
            <h2 id="arrival-title">
              Your visa is only part of staying legally
            </h2>
            <p>
              Foreign visitors generally must register their place of stay
              within three working days. Hotels handle registration for guests;
              private hosts use the government system or territorial authority.
              Keep registration evidence and update it when accommodation
              changes.
            </p>
          </div>
          <div className="arrival-actions">
            <ExternalLink
              className="pill pill-light"
              href={FOREIGNER_SERVICES_URL}
            >
              Foreigners on my.gov.uz
            </ExternalLink>
            <a className="text-link" href="#overstay-note">
              Read the overstay warning <Arrow />
            </a>
          </div>
        </section>

        <aside
          className="warning-note"
          id="overstay-note"
          aria-labelledby="warning-title"
        >
          <span className="warning-mark" aria-hidden="true">
            !
          </span>
          <div>
            <h2 id="warning-title">
              Do not wait until departure to resolve an overstay
            </h2>
            <p>
              Overstaying or missing registration can lead to administrative
              fines, exit formalities, deportation, or an entry ban. If you may
              be out of status, contact the local Migration and Citizenship
              Department immediately. Penalties and the base calculation amount
              can change.
            </p>
          </div>
        </aside>

        <section className="official-sources" aria-labelledby="sources-title">
          <div>
            <p className="section-kicker">Official next steps</p>
            <h2 id="sources-title">Verify, then apply</h2>
            <p>
              Uzbekistan OS organizes the rules. Government portals and consular
              officers make eligibility and issuance decisions.
            </p>
          </div>
          <div className="source-links">
            <a className="pill pill-dark" href="/signup">
              <span>Create your visa plan</span>
              <Arrow variant="white" />
            </a>
            <ExternalLink
              className="pill pill-light"
              href={OFFICIAL_E_VISA_URL}
            >
              Official e-Visa portal
            </ExternalLink>
            <ExternalLink className="pill pill-light" href={OFFICIAL_VISA_URL}>
              MFA visa catalogue
            </ExternalLink>
            <ExternalLink
              className="pill pill-light"
              href={FOREIGNER_SERVICES_URL}
            >
              Services for foreigners
            </ExternalLink>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="footer-assurance">
          <span className="footer-icon">
            <Image alt="" height={24} src="/landing/verified.svg" width={24} />
          </span>
          <div>
            <strong>Visa guidance grounded in official sources.</strong>
            <span>Last content review: 9 August 2026.</span>
          </div>
        </div>
        <div className="footer-navigation">
          <nav className="footer-legal" aria-label="Legal">
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Use</a>
          </nav>
          <a className="footer-link" href="#top">
            <span>Back to top</span>
            <Image
              alt=""
              height={16}
              src="/landing/arrow-footer.svg"
              width={16}
            />
          </a>
        </div>
      </footer>
    </div>
  );
}
