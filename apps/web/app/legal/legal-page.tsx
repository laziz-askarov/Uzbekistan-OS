import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./legal-page.module.css";

type LegalSection = {
  id: string;
  title: string;
  content: ReactNode;
};

type LegalPageProps = {
  description: string;
  effectiveDate: string;
  eyebrow: string;
  sections: LegalSection[];
  summary: ReactNode;
  title: string;
};

export default function LegalPage({
  description,
  effectiveDate,
  eyebrow,
  sections,
  summary,
  title,
}: LegalPageProps) {
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/" aria-label="Uzbekistan OS home">
          Uzbekistan OS
        </Link>
        <Link className={styles.back} href="/">
          Return home
        </Link>
      </header>

      <article className={styles.article}>
        <div className={styles.hero}>
          <p className={styles.eyebrow}>{eyebrow}</p>
          <h1>{title}</h1>
          <p className={styles.description}>{description}</p>
          <p className={styles.effective}>Effective {effectiveDate}</p>
        </div>

        <aside className={styles.summary} aria-labelledby="summary-title">
          <p className={styles.summaryLabel} id="summary-title">
            In plain language
          </p>
          {summary}
        </aside>

        <div className={styles.layout}>
          <nav className={styles.contents} aria-label={`${title} sections`}>
            <p>On this page</p>
            <ol>
              {sections.map((section) => (
                <li key={section.id}>
                  <a href={`#${section.id}`}>{section.title}</a>
                </li>
              ))}
            </ol>
          </nav>

          <div className={styles.sections}>
            {sections.map((section, index) => (
              <section id={section.id} key={section.id}>
                <p className={styles.sectionNumber}>
                  {String(index + 1).padStart(2, "0")}
                </p>
                <h2>{section.title}</h2>
                {section.content}
              </section>
            ))}
          </div>
        </div>
      </article>

      <footer className={styles.footer}>
        <span>Uzbekistan OS · Tashkent, Uzbekistan</span>
        <nav aria-label="Legal pages">
          <Link href="/privacy">Privacy Policy</Link>
          <Link href="/terms">Terms of Use</Link>
          <a href="mailto:info@uzbekistanos.com">info@uzbekistanos.com</a>
        </nav>
      </footer>
    </main>
  );
}
