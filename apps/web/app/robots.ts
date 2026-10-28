import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/editorial-content";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/account/", "/admin/", "/api/", "/auth/", "/chat"],
      },
      {
        userAgent: [
          "OAI-SearchBot",
          "Claude-SearchBot",
          "Claude-User",
          "Googlebot",
          "Bingbot",
        ],
        allow: "/",
        disallow: ["/account/", "/admin/", "/api/", "/auth/", "/chat"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
