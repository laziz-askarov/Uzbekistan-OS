import type { PublishedPostSummary } from "@/lib/editorial-content";

export type AuthorProfile = {
  slug: string;
  name: string;
  posts: PublishedPostSummary[];
  guideCount: number;
  latestAt: string | null;
};

const slugPattern = /^[a-z0-9][a-z0-9-]{0,80}$/;

export function isAuthorSlug(value: string) {
  return slugPattern.test(value);
}

function newestFirst(a: PublishedPostSummary, b: PublishedPostSummary) {
  return b.published_at.localeCompare(a.published_at);
}

export function buildAuthorProfiles(
  posts: PublishedPostSummary[],
): AuthorProfile[] {
  const byAuthor = new Map<string, AuthorProfile>();
  for (const post of posts) {
    if (!isAuthorSlug(post.author_slug)) continue;
    const profile = byAuthor.get(post.author_slug) ?? {
      slug: post.author_slug,
      name: post.author_name,
      posts: [],
      guideCount: 0,
      latestAt: null,
    };
    profile.posts = [...profile.posts, post].sort(newestFirst);
    profile.guideCount = profile.posts.length;
    profile.latestAt = profile.posts[0]?.published_at ?? null;
    byAuthor.set(post.author_slug, profile);
  }
  return [...byAuthor.values()].sort((a, b) => a.name.localeCompare(b.name));
}

export function findAuthorProfile(
  posts: PublishedPostSummary[],
  slug: string,
): AuthorProfile | null {
  if (!isAuthorSlug(slug)) return null;
  return (
    buildAuthorProfiles(posts).find((profile) => profile.slug === slug) ?? null
  );
}

/**
 * Where a byline should point: a verified external profile when the author
 * set one, otherwise the on-site author page, otherwise the about page.
 */
export function authorPageUrl(
  author: { slug: string; profile_url: string | null },
  siteUrl: string,
) {
  if (author.profile_url) {
    try {
      const url = new URL(author.profile_url);
      if (url.protocol === "https:") return url.toString();
    } catch {
      // Fall through to the on-site profile.
    }
  }
  return isAuthorSlug(author.slug)
    ? `${siteUrl}/authors/${author.slug}`
    : `${siteUrl}/about`;
}
