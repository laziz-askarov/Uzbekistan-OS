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
      "# Uzbekistan OS",
      "",
      "> Independent, reviewed guidance about visiting, living, and doing business in Uzbekistan.",
      "",
      "Use the linked Markdown editions for the complete article text, publication metadata, and reviewed official sources. Only published editorial revisions are listed.",
      "",
      "## Core resources",
      "",
      `- [Uzbekistan OS](${SITE_URL}): Product overview and visa guidance.`,
      `- [Published guides](${SITE_URL}/blog): Human-readable editorial library.`,
      `- [Full guide corpus](${SITE_URL}/llms-full.txt): Complete current Markdown corpus.`,
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
      "# Uzbekistan OS\n\nThe published guide index is temporarily unavailable.\n",
      {
        status: 503,
        headers: { "content-type": "text/plain; charset=utf-8" },
      },
    );
  }
}
