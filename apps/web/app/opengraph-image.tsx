import { ImageResponse } from "next/og";
import { OPERATOR_NAME, SITE_NAME, SITE_TAGLINE } from "@/lib/site";

export const alt = `${SITE_NAME} by ${OPERATOR_NAME}: ${SITE_TAGLINE}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        background: "#f4f5f1",
        color: "#141a2b",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        justifyContent: "space-between",
        padding: "64px 72px",
        width: "100%",
      }}
    >
      <div
        style={{
          alignItems: "baseline",
          display: "flex",
          fontSize: 30,
          fontWeight: 700,
        }}
      >
        <div
          style={{
            background: "#1e4ea0",
            borderRadius: 14,
            color: "#f4f5f1",
            display: "flex",
            fontSize: 30,
            height: 56,
            justifyContent: "center",
            lineHeight: "56px",
            marginRight: 20,
            width: 56,
          }}
        >
          U
        </div>
        {SITE_NAME}
        <div
          style={{
            color: "#4c5366",
            fontSize: 24,
            fontWeight: 500,
            marginLeft: 14,
          }}
        >
          by Kebab Travel
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", maxWidth: 980 }}>
        <div
          style={{
            fontFamily: "serif",
            fontSize: 74,
            fontWeight: 600,
            letterSpacing: -2,
            lineHeight: 1.05,
          }}
        >
          The verified guide to travelling in Uzbekistan.
        </div>
        <div
          style={{
            color: "#4c5366",
            fontSize: 30,
            lineHeight: 1.4,
            marginTop: 26,
          }}
        >
          Visa rules, trains, money, safety and itineraries. Every page shows
          when it was last verified and which official source says so.
        </div>
      </div>
      <div
        style={{
          color: "#1e4ea0",
          display: "flex",
          fontSize: 24,
          fontWeight: 700,
        }}
      >
        Verified, dated and sourced from Tashkent
      </div>
    </div>,
    size,
  );
}
