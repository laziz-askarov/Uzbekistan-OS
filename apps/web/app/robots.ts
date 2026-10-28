import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/editorial-content";

const privatePaths = ["/account/", "/admin/", "/api/", "/auth/", "/chat"];

// Search engines and AI answer engines are welcome on every public page; the
// signed-in assistant and administration surfaces stay out of every index.
const welcomeCrawlers = [
  "Googlebot",
  "Bingbot",
  "GPTBot",
  "OAI-SearchBot",
  "ClaudeBot",
  "Claude-SearchBot",
  "Claude-User",
  "PerplexityBot",
  "Google-Extended",
  "Applebot",
  "CCBot",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: privatePaths },
      { userAgent: welcomeCrawlers, allow: "/", disallow: privatePaths },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
