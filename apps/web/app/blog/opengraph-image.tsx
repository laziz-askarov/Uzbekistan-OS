import { ImageResponse } from "next/og";

export const alt = "Uzbekistan OS reviewed guides";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function BlogOpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        background:
          "linear-gradient(135deg, #07162f 0%, #0f2e61 62%, #2563eb 100%)",
        color: "white",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        justifyContent: "space-between",
        padding: "64px 72px",
        width: "100%",
      }}
    >
      <div style={{ display: "flex", fontSize: 27, fontWeight: 700 }}>
        Uzbekistan OS / Guides
      </div>
      <div style={{ display: "flex", flexDirection: "column", maxWidth: 1000 }}>
        <div
          style={{
            fontSize: 76,
            fontWeight: 800,
            letterSpacing: -3,
            lineHeight: 1.02,
          }}
        >
          Practical guides built on reviewed sources.
        </div>
        <div
          style={{
            color: "#bfdbfe",
            fontSize: 30,
            lineHeight: 1.35,
            marginTop: 28,
          }}
        >
          Tourism · Business · Immigration · Healthcare · Everyday living
        </div>
      </div>
      <div style={{ display: "flex", fontSize: 23, opacity: 0.88 }}>
        uzbekistanos.com/blog
      </div>
    </div>,
    size,
  );
}
