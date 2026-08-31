import { ImageResponse } from "next/og";

export const alt = "Uzbekistan OS — trusted guidance for Uzbekistan";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "stretch",
        background: "#f8fafc",
        color: "#0f172a",
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
          alignItems: "center",
          display: "flex",
          fontSize: 28,
          fontWeight: 700,
        }}
      >
        <div
          style={{
            alignItems: "center",
            background: "#2563eb",
            borderRadius: 20,
            color: "white",
            display: "flex",
            height: 64,
            justifyContent: "center",
            marginRight: 22,
            width: 64,
          }}
        >
          U
        </div>
        Uzbekistan OS
      </div>
      <div style={{ display: "flex", flexDirection: "column", maxWidth: 980 }}>
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            letterSpacing: -3,
            lineHeight: 1.04,
          }}
        >
          Uzbekistan, explained clearly.
        </div>
        <div
          style={{
            color: "#475569",
            fontSize: 32,
            lineHeight: 1.35,
            marginTop: 28,
          }}
        >
          Reviewed guidance for visiting, living, and doing business.
        </div>
      </div>
      <div
        style={{
          color: "#2563eb",
          display: "flex",
          fontSize: 24,
          fontWeight: 700,
        }}
      >
        Sources you can inspect · Dates you can trust
      </div>
    </div>,
    size,
  );
}
