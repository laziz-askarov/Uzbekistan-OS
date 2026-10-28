import Link from "next/link";
import { OPERATOR_NAME, PRIMARY_NAVIGATION, SITE_NAME } from "@/lib/site";
import styles from "./site.module.css";

type SiteHeaderProps = {
  current?: string;
};

export function SiteHeader({ current }: SiteHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link
          className={styles.brand}
          href="/"
          aria-label={`${SITE_NAME} home`}
        >
          <span className={styles.mark} aria-hidden="true">
            U
          </span>
          <span className={styles.wordmark}>
            <strong>{SITE_NAME}</strong>
            <small>by {OPERATOR_NAME}</small>
          </span>
        </Link>
        <nav className={styles.nav} aria-label="Main navigation">
          {PRIMARY_NAVIGATION.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={item.emphasis ? styles.cta : undefined}
              aria-current={current === item.href ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
