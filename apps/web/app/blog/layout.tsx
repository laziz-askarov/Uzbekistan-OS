import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
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
      <SiteHeader current="/travel" />
      <main className={styles.main}>{children}</main>
      <SiteFooter />
    </div>
  );
}
