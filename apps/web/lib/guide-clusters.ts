import type { PublishedPostSummary } from "@/lib/editorial-content";

export type GuideCluster = {
  id: string;
  title: string;
  description: string;
  slugs: readonly string[];
};

export type ClusterGroup = Omit<GuideCluster, "slugs"> & {
  posts: PublishedPostSummary[];
};

/**
 * Editorial order for the travel hub. Slugs are the published English guides;
 * a guide that is not listed still appears under "More travel guides".
 */
export const TRAVEL_CLUSTERS: readonly GuideCluster[] = [
  {
    id: "before-you-go",
    title: "Before you go",
    description:
      "Entry rules, registration, money, phones, safety and what to pack, each checked against the official source.",
    slugs: [
      "uzbekistan-visa-requirements",
      "uzbekistan-tourist-registration",
      "is-uzbekistan-safe",
      "best-time-to-visit-uzbekistan",
      "uzbekistan-trip-cost",
      "money-in-uzbekistan",
      "uzbekistan-sim-cards-esims-internet",
      "uzbekistan-packing-list",
    ],
  },
  {
    id: "getting-around",
    title: "Getting around",
    description:
      "Airport arrival, the Afrosiyob and other trains, flights, taxis and the checks that keep bookings valid.",
    slugs: ["arriving-in-tashkent", "getting-around-uzbekistan"],
  },
  {
    id: "where-to-go",
    title: "Where to go",
    description:
      "The classic route through Tashkent, Samarkand, Bukhara and Khiva, and where to stay in each city.",
    slugs: ["visiting-uzbekistan-first-time", "where-to-stay-in-uzbekistan"],
  },
  {
    id: "culture-and-food",
    title: "Culture and food",
    description:
      "What to eat, how markets work, and the customs worth knowing before you sit down to plov.",
    slugs: ["what-to-eat-in-uzbekistan"],
  },
];

export const MORE_TRAVEL_CLUSTER = {
  id: "more-guides",
  title: "More travel guides",
  description: "Recently published guides that have not been grouped yet.",
} as const;

export type LivingDomain = {
  slug: string;
  title: string;
  description: string;
};

export const LIVING_DOMAINS: readonly LivingDomain[] = [
  {
    slug: "immigration",
    title: "Immigration and residence",
    description:
      "Registration after arrival, extensions, residence permits and work authorization.",
  },
  {
    slug: "everyday-living",
    title: "Everyday life",
    description:
      "Bank accounts, PINFL, renting, utilities and the paperwork of settling in.",
  },
  {
    slug: "business-registration",
    title: "Business",
    description: "Starting a company, taxes, banking and compliance.",
  },
  {
    slug: "healthcare",
    title: "Healthcare",
    description: "Insurance, clinics, emergencies and vaccinations.",
  },
];

function orderBySlugs(posts: PublishedPostSummary[], slugs: readonly string[]) {
  return slugs.flatMap((slug) => {
    const post = posts.find((candidate) => candidate.slug === slug);
    return post ? [post] : [];
  });
}

export function groupTravelGuides(
  posts: PublishedPostSummary[],
  language = "en",
): ClusterGroup[] {
  const travel = posts.filter(
    (post) => post.domain_slug === "tourism" && post.language_code === language,
  );
  const groups = TRAVEL_CLUSTERS.map(({ slugs, ...cluster }) => ({
    ...cluster,
    posts: orderBySlugs(travel, slugs),
  }));
  const grouped = new Set(
    groups.flatMap((group) => group.posts.map((p) => p.slug)),
  );
  const rest = travel.filter((post) => !grouped.has(post.slug));
  return rest.length
    ? [...groups, { ...MORE_TRAVEL_CLUSTER, posts: rest }]
    : groups;
}

export type LivingGroup = LivingDomain & { posts: PublishedPostSummary[] };

export function groupLivingGuides(
  posts: PublishedPostSummary[],
  language = "en",
): LivingGroup[] {
  return LIVING_DOMAINS.flatMap((domain) => {
    const matching = posts.filter(
      (post) =>
        post.domain_slug === domain.slug && post.language_code === language,
    );
    return matching.length ? [{ ...domain, posts: matching }] : [];
  });
}

export function latestVerification(posts: PublishedPostSummary[]) {
  return posts.reduce<string | null>((latest, post) => {
    if (!post.updated_at) return latest;
    return !latest || post.updated_at > latest ? post.updated_at : latest;
  }, null);
}
