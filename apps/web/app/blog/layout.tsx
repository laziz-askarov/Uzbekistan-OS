import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SITE_URL } from "@/lib/editorial-content";
import styles from "./blog.module.css";

export const metadata: Metadata = {
  alternates: {
    types: {
      "application/rss+xml": `${SITE_URL}/blog/rss.xml`,
    },
  },
};

export default function BlogLayout({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/">
          <span className={styles.brandMark} aria-hidden="true">
            U
          </span>
          Uzbekistan OS
        </Link>
        <nav className={styles.nav} aria-label="Main navigation">
          <Link href="/blog">Guides</Link>
          <Link href="/">Visa overview</Link>
          <Link className={styles.cta} href="/signup">
            Open assistant
          </Link>
        </nav>
      </header>
      <main className={styles.main}>{children}</main>
      <footer className={styles.footer}>
        <span>Independent guidance about Uzbekistan.</span>
        <nav aria-label="Footer navigation">
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/blog/rss.xml">RSS</Link>
          <Link href="/llms.txt">LLM index</Link>
        </nav>
      </footer>
    </div>
  );
}
