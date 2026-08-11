import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "@uzbekistan-os/design-system/components.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Uzbekistan visa guide | Uzbekistan OS",
  description:
    "Evidence-backed guidance for visa-free entry, e-visas, consular visas, and registration in Uzbekistan.",
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
