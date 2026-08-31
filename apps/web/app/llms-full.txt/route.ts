import {
  getPublishedPost,
  listPublishedPosts,
  publicPostUrl,
} from "@/lib/editorial-content";

export const runtime = "nodejs";

export async function GET() {
  try {
    const summaries = await listPublishedPosts({ limit: 100 });
    const posts = (
      await Promise.all(
        summaries.map((summary) => getPublishedPost(summary.slug)),
      )
    ).filter((post) => post !== null);
    const body = [
      "# Uzbekistan OS — complete published guide corpus",
      "",
      "> Current published editorial revisions with transparent authorship and reviewed source lineage.",
      "",
      ...posts.flatMap((post) => [
        `# ${post.title}`,
        "",
        `Canonical URL: ${post.canonical_url ?? publicPostUrl(post.slug)}`,
        `Language: ${post.language_code}`,
        `Topic: ${post.domain_slug ?? "Uzbekistan"}`,
        `Author: ${post.author.name}`,
        `Published: ${post.published_at}`,
        `Updated: ${post.updated_at}`,
        "",
        post.summary,
        "",
        post.body_markdown,
        "",
        "## Sources",
        "",
        ...post.sources.map(
          (source, index) =>
            `${index + 1}. [${source.title}](${source.url}) — ${source.organization}; ${source.locator}`,
        ),
        "",
        "---",
        "",
      ]),
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
      "# Uzbekistan OS\n\nThe guide corpus is temporarily unavailable.\n",
      {
        status: 503,
        headers: { "content-type": "text/plain; charset=utf-8" },
      },
    );
  }
}
