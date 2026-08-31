import { ImageResponse } from "next/og";
import { getPublishedPost } from "@/lib/editorial-content";

export const alt = "Uzbekistan OS guide";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

type ImageProps = { params: Promise<{ slug: string }> };

export default async function ArticleOpenGraphImage({ params }: ImageProps) {
  const { slug } = await params;
  const post = await getPublishedPost(slug);
  const title = post?.title ?? "Uzbekistan OS guide";
  const domain = post?.domain_slug?.replaceAll("-", " ") ?? "Uzbekistan";
  const fontSize = title.length > 86 ? 54 : title.length > 58 ? 62 : 72;

  return new ImageResponse(
    <div
      style={{
        background: "#f8fafc",
        color: "#0f172a",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        justifyContent: "space-between",
        padding: "58px 68px",
        width: "100%",
      }}
    >
      <div
        style={{
          alignItems: "center",
          color: "#2563eb",
          display: "flex",
          fontSize: 25,
          fontWeight: 800,
        }}
      >
        UZBEKISTAN OS{" "}
        <span style={{ color: "#94a3b8", margin: "0 14px" }}>·</span>{" "}
        {domain.toUpperCase()}
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div
          style={{
            fontSize,
            fontWeight: 800,
            letterSpacing: -2.5,
            lineHeight: 1.06,
            maxWidth: 1060,
          }}
        >
          {title}
        </div>
        <div
          style={{
            background: "#dbeafe",
            borderRadius: 999,
            color: "#1d4ed8",
            display: "flex",
            fontSize: 22,
            fontWeight: 700,
            marginTop: 34,
            padding: "11px 20px",
            width: "fit-content",
          }}
        >
          Reviewed sources included
        </div>
      </div>
      <div style={{ color: "#64748b", display: "flex", fontSize: 22 }}>
        {post
          ? `By ${post.author.name} · Updated ${post.updated_at.slice(0, 10)}`
          : "Independent guidance about Uzbekistan"}
      </div>
    </div>,
    size,
  );
}
