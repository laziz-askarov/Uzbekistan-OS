import { getPublishedPost, publicPostUrl } from "@/lib/editorial-content";

export const runtime = "nodejs";

export async function GET(
  _: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const post = await getPublishedPost(slug);
  if (!post) {
    return new Response("Published guide not found.\n", {
      status: 404,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }

  const metadata = [
    `# ${post.title}`,
    "",
    `> ${post.summary}`,
    "",
    `- Canonical URL: ${post.canonical_url ?? publicPostUrl(post.slug)}`,
    `- Language: ${post.language_code}`,
    `- Topic: ${post.domain_slug ?? "Uzbekistan"}`,
    `- Content type: ${post.content_type}`,
    `- Author: ${post.author.name}`,
    `- Published: ${post.published_at}`,
    `- Updated: ${post.updated_at}`,
    `- Editorial version: ${post.version_number}`,
    "",
  ];
  const sources = post.sources.length
    ? [
        "## Reviewed sources",
        "",
        ...post.sources.map((source, index) => {
          const provenance = source.document_title
            ? `; reviewed knowledge: ${source.document_title}${source.reviewed_at ? ` (reviewed ${source.reviewed_at})` : ""}`
            : "";
          return `${index + 1}. [${source.title}](${source.url}) — ${source.organization}; ${source.locator}${provenance}`;
        }),
        "",
      ]
    : [];
  const structured = Object.keys(post.structured_content).length
    ? [
        "## Structured content",
        "",
        "```json",
        JSON.stringify(post.structured_content, null, 2),
        "```",
        "",
      ]
    : [];
  const body = [
    ...metadata,
    post.body_markdown,
    "",
    ...sources,
    ...structured,
  ].join("\n");

  return new Response(body, {
    headers: {
      "cache-control": "public, s-maxage=300, stale-while-revalidate=3600",
      "content-type": "text/markdown; charset=utf-8",
      "x-content-type-options": "nosniff",
    },
  });
}
