import type { Metadata } from "next";
import {
  Fraunces,
  Instrument_Sans,
  Instrument_Serif,
  Inter,
} from "next/font/google";
import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "@uzbekistan-os/design-system/components.css";
import { JsonLd } from "@/components/site/json-ld";
import { SITE_URL } from "@/lib/editorial-content";
import { organizationGraph } from "@/lib/organization-schema";
import {
  OPERATOR_NAME,
  SITE_DESCRIPTION,
  SITE_LOCKUP,
  SITE_NAME,
  SITE_TAGLINE,
} from "@/lib/site";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  axes: ["opsz", "SOFT"],
  display: "swap",
  variable: "--font-fraunces",
});

const text = Inter({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-inter",
});

// Editorial preview faces; they replace Fraunces and Inter once approved.
const magazineDisplay = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-instrument-serif",
});

const magazineText = Instrument_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-instrument-sans",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: SITE_NAME,
  title:
    "Uzbekistan OS by Kebab Travel | The verified guide to travelling in Uzbekistan",
  description: SITE_DESCRIPTION,
  alternates: {
    canonical: SITE_URL,
    types: {
      "application/rss+xml": `${SITE_URL}/blog/rss.xml`,
    },
  },
  category: "travel",
  creator: OPERATOR_NAME,
  publisher: OPERATOR_NAME,
  keywords: [
    "Uzbekistan travel",
    "Uzbekistan travel guide",
    "Samarkand",
    "Bukhara",
    "Khiva",
    "Tashkent",
    "living in Uzbekistan",
  ],
  openGraph: {
    type: "website",
    siteName: SITE_LOCKUP,
    url: SITE_URL,
    title: `${SITE_NAME} | ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    images: [
      {
        url: `${SITE_URL}/opengraph-image`,
        width: 1200,
        height: 630,
        alt: `${SITE_NAME} by ${OPERATOR_NAME}: ${SITE_TAGLINE}`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} | ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    images: [`${SITE_URL}/opengraph-image`],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${text.variable} ${magazineDisplay.variable} ${magazineText.variable}`}
    >
      <body>
        <JsonLd data={organizationGraph(SITE_URL)} />
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
