import {
  listPublishedPosts,
  publicPostUrl,
  SITE_URL,
} from "@/lib/editorial-content";

// The feed depends on the separately deployed grounded API. Generate it at
// request time so a temporary API outage cannot break a web deployment; the
// response remains cached at the CDN for one hour.
export const dynamic = "force-dynamic";

function escapeXml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function rssDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? new Date(0).toUTCString()
    : date.toUTCString();
}

export async function GET() {
  const posts = await listPublishedPosts({ limit: 100 });
  const lastBuildDate = posts.reduce<string | null>((latest, post) => {
    if (!latest) return post.updated_at;
    return new Date(post.updated_at) > new Date(latest)
      ? post.updated_at
      : latest;
  }, null);
  const items = posts
    .map((post) => {
      const url = publicPostUrl(post.slug);
      return [
        "    <item>",
        `      <title>${escapeXml(post.title)}</title>`,
        `      <link>${escapeXml(url)}</link>`,
        `      <guid isPermaLink="true">${escapeXml(url)}</guid>`,
        `      <description>${escapeXml(post.summary)}</description>`,
        `      <dc:creator>${escapeXml(post.author_name)}</dc:creator>`,
        `      <category>${escapeXml(post.domain_slug ?? "Uzbekistan")}</category>`,
        `      <pubDate>${rssDate(post.published_at)}</pubDate>`,
        "    </item>",
      ].join("\n");
    })
    .join("\n");

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">',
    "  <channel>",
    "    <title>Uzbekistan OS Guides</title>",
    `    <link>${SITE_URL}/blog</link>`,
    "    <description>Reviewed guides about visiting, living, and doing business in Uzbekistan.</description>",
    "    <language>en</language>",
    `    <lastBuildDate>${rssDate(lastBuildDate ?? new Date().toISOString())}</lastBuildDate>`,
    `    <atom:link href="${SITE_URL}/blog/rss.xml" rel="self" type="application/rss+xml" />`,
    items,
    "  </channel>",
    "</rss>",
    "",
  ].join("\n");

  return new Response(xml, {
    headers: {
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
      "Content-Type": "application/rss+xml; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
