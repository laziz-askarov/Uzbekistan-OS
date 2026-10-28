import Link from "next/link";
import {
  CONTACT_EMAIL,
  FOOTER_NAVIGATION,
  OPERATOR_CITY,
  OPERATOR_NAME,
  POLICY_NAVIGATION,
  SITE_NAME,
} from "@/lib/site";
import styles from "./site.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        <div className={styles.footerStatement}>
          <strong>
            {SITE_NAME} by {OPERATOR_NAME}
          </strong>
          <p>
            {SITE_NAME} is published by {OPERATOR_NAME}, a travel company in{" "}
            {OPERATOR_CITY}. Every guide is dated and tied to the official
            source behind it. Guides are independent of the trips we plan;{" "}
            <Link href="/about#independence">read how we keep them apart</Link>.
          </p>
          <p>
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          </p>
        </div>
        <nav aria-labelledby="footer-explore">
          <h2 id="footer-explore">Explore</h2>
          <ul>
            {FOOTER_NAVIGATION.map((item) => (
              <li key={item.href}>
                <Link href={item.href}>{item.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-labelledby="footer-policies">
          <h2 id="footer-policies">Policies and feeds</h2>
          <ul>
            {POLICY_NAVIGATION.map((item) => (
              <li key={item.href}>
                <Link href={item.href}>{item.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className={styles.footerBottom}>
        <span>
          © {new Date().getUTCFullYear()} {OPERATOR_NAME}, {OPERATOR_CITY},
          Uzbekistan
        </span>
        <span>
          Guidance, not legal advice. Confirm rules with the official source
          before you travel.
        </span>
      </div>
    </footer>
  );
}
