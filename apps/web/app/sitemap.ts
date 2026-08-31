import type { MetadataRoute } from "next";
import {
  listPublishedPosts,
  publicPostUrl,
  SITE_URL,
} from "@/lib/editorial-content";

export const revalidate = 3600;

function sitemapImage(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/blog`,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/privacy`,
      changeFrequency: "yearly",
      priority: 0.2,
    },
    {
      url: `${SITE_URL}/terms`,
      changeFrequency: "yearly",
      priority: 0.2,
    },
  ];
  try {
    const posts = await listPublishedPosts({ limit: 100 });
    return [
      ...staticPages,
      ...posts.map((post) => {
        const image = sitemapImage(post.hero_image_url);
        return {
          url: publicPostUrl(post.slug),
          lastModified: post.updated_at,
          changeFrequency: "weekly" as const,
          priority: 0.8,
          ...(image ? { images: [image] } : {}),
        };
      }),
    ];
  } catch {
    return staticPages;
  }
}
