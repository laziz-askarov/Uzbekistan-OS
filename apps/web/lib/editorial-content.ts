import "server-only";

import { cache } from "react";

const editorialApiBase = (
  process.env.GROUNDED_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://www.uzbekistanos.com"
).replace(/\/$/, "");

export type PublishedPostSummary = {
  id: string;
  slug: string;
  content_type: "article" | "guide" | "platform_update" | "interview";
  domain_slug: string | null;
  language_code: string;
  title: string;
  summary: string;
  hero_image_url: string | null;
  hero_image_alt: string | null;
  author_name: string;
  author_slug: string;
  published_at: string;
  updated_at: string;
};

export type PublishedSource = {
  source_id: string;
  title: string;
  organization: string;
  url: string;
  locator: string;
};

export type PublishedPost = {
  id: string;
  version_id: string;
  version_number: number;
  slug: string;
  content_type: PublishedPostSummary["content_type"];
  domain_slug: string | null;
  language_code: string;
  title: string;
  summary: string;
  body_markdown: string;
  structured_content: Record<string, unknown>;
  seo_title: string | null;
  seo_description: string | null;
  canonical_url: string | null;
  hero_image_url: string | null;
  hero_image_alt: string | null;
  author: {
    slug: string;
    name: string;
    bio: string | null;
    avatar_url: string | null;
    profile_url: string | null;
  };
  sources: PublishedSource[];
  translations: Array<{
    language_code: string;
    slug: string;
    title: string;
  }>;
  published_at: string;
  updated_at: string;
  review_due_at: string | null;
};

type Envelope<T> = { data: T; meta: { request_id: string | null } };

async function editorialRequest<T>(path: string): Promise<T> {
  const response = await fetch(`${editorialApiBase}${path}`, {
    headers: { accept: "application/json" },
    next: { revalidate: 300, tags: ["editorial-content"] },
  });
  if (!response.ok) {
    throw new EditorialContentError(response.status, path);
  }
  const payload = (await response.json()) as Envelope<T>;
  return payload.data;
}

export class EditorialContentError extends Error {
  constructor(
    readonly status: number,
    path: string,
  ) {
    super(`Editorial API request failed with status ${status} for ${path}.`);
  }
}

export async function listPublishedPosts(options?: {
  domain?: string;
  language?: string;
  limit?: number;
}): Promise<PublishedPostSummary[]> {
  const params = new URLSearchParams();
  if (options?.domain) params.set("domain", options.domain);
  if (options?.language) params.set("language", options.language);
  params.set("limit", String(options?.limit ?? 100));
  return editorialRequest<PublishedPostSummary[]>(
    `/content/posts?${params.toString()}`,
  );
}

export const getPublishedPost = cache(
  async (slug: string): Promise<PublishedPost | null> => {
    try {
      return await editorialRequest<PublishedPost>(
        `/content/posts/${encodeURIComponent(slug)}`,
      );
    } catch (error) {
      if (error instanceof EditorialContentError && error.status === 404) {
        return null;
      }
      throw error;
    }
  },
);

export function publicPostUrl(slug: string) {
  return `${SITE_URL}/blog/${slug}`;
}
