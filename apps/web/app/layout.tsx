import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "@uzbekistan-os/design-system/components.css";
import { SITE_URL } from "@/lib/editorial-content";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: "Uzbekistan OS",
  title: "Uzbekistan OS | Trusted guides for visiting, living and business",
  description:
    "Reviewed guidance about visiting, living, doing business, healthcare, and immigration in Uzbekistan, with transparent sources and update dates.",
  alternates: {
    canonical: SITE_URL,
    types: {
      "application/rss+xml": `${SITE_URL}/blog/rss.xml`,
    },
  },
  category: "travel and public information",
  creator: "Uzbekistan OS",
  publisher: "Uzbekistan OS",
  keywords: [
    "Uzbekistan",
    "Uzbekistan travel",
    "Uzbekistan business",
    "living in Uzbekistan",
    "Uzbekistan immigration",
  ],
  openGraph: {
    type: "website",
    siteName: "Uzbekistan OS",
    url: SITE_URL,
    title: "Uzbekistan OS",
    description:
      "Reviewed guidance for visiting, living, and doing business in Uzbekistan.",
    images: [
      {
        url: `${SITE_URL}/opengraph-image`,
        width: 1200,
        height: 630,
        alt: "Uzbekistan OS — trusted guidance for Uzbekistan",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Uzbekistan OS",
    description:
      "Reviewed guidance for visiting, living, and doing business in Uzbekistan.",
    images: [`${SITE_URL}/opengraph-image`],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
