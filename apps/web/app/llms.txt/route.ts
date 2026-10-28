import {
  listPublishedPosts,
  publicPostUrl,
  SITE_URL,
} from "@/lib/editorial-content";

export const runtime = "nodejs";

export async function GET() {
  try {
    const posts = await listPublishedPosts({ limit: 100 });
    const body = [
      "# Uzbekistan OS by Kebab Travel",
      "",
      "> The verified guide to travelling in and living in Uzbekistan. Every guide is dated, tied to an official source, and written by a Tashkent-based team. Published by Kebab Travel, a Tashkent travel company.",
      "",
      "Use the linked Markdown editions for the complete article text, publication metadata, verification dates, and reviewed official sources. Only published editorial revisions are listed.",
      "",
      "## Core resources",
      "",
      `- [Uzbekistan OS](${SITE_URL}): Home: verified travel guidance for visitors from the US and Europe.`,
      `- [Travel guides](${SITE_URL}/travel): Before you go, getting around, where to go, culture and food.`,
      `- [Living in Uzbekistan](${SITE_URL}/living): Immigration, everyday life, business and healthcare guides.`,
      `- [All guides](${SITE_URL}/blog): Chronological editorial library in English, Uzbek and Russian.`,
      `- [Full guide corpus](${SITE_URL}/llms-full.txt): Complete current Markdown corpus.`,
      `- [About and methodology](${SITE_URL}/about): Who writes the guides, how facts are verified, editorial independence.`,
      `- [Plan a trip with Kebab Travel](${SITE_URL}/trips): Trip planning service and inquiry form.`,
      "",
      "## Published guides",
      "",
      ...posts.map(
        (post) =>
          `- [${post.title}](${publicPostUrl(post.slug)}/markdown): ${post.summary}`,
      ),
      "",
      "## Policies",
      "",
      `- [Privacy policy](${SITE_URL}/privacy)`,
      `- [Terms of use](${SITE_URL}/terms)`,
      "",
    ].join("\n");
    return new Response(body, {
      headers: {
        "cache-control": "public, s-maxage=300, stale-while-revalidate=3600",
        "content-type": "text/plain; charset=utf-8",
        "x-content-type-options": "nosniff",
      },
    });
  } catch {
    return new Response(
      "# Uzbekistan OS by Kebab Travel\n\nThe published guide index is temporarily unavailable.\n",
      {
        status: 503,
        headers: { "content-type": "text/plain; charset=utf-8" },
      },
    );
  }
}
