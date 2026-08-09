import type { Metadata } from "next";
import type { ReactNode } from "react";
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
      <body>{children}</body>
    </html>
  );
}
