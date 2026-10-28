import type { PublishedPostSummary } from "@/lib/editorial-content";

/**
 * The brand kit names four sections and gives each a highlight colour:
 * Visas & documents (cobalt), Money (saffron), Getting around (turquoise)
 * and Living here (pomegranate). Planning guides (routes, seasons, stays,
 * food, safety, phones) carry the neutral ink tile, because the kit reserves
 * colour for those four.
 */
export type BrandSectionId =
  "visas" | "money" | "transport" | "planning" | "living";

export type BrandSection = {
  id: BrandSectionId;
  title: string;
  description: string;
  href: string;
};

export const BRAND_SECTIONS: readonly BrandSection[] = [
  {
    id: "visas",
    title: "Visas and documents",
    description:
      "Entry rules, e-visas, registration after arrival and what to carry.",
    href: "/travel#before-you-go",
  },
  {
    id: "money",
    title: "Money",
    description:
      "Real prices, which cards work where, ATMs, exchange and tipping.",
    href: "/travel#before-you-go",
  },
  {
    id: "transport",
    title: "Getting around",
    description:
      "Airport arrival, the Afrosiyob train, flights, taxis and booking checks.",
    href: "/travel#getting-around",
  },
  {
    id: "planning",
    title: "Planning the trip",
    description:
      "Routes, seasons, where to stay, what to eat, safety and staying connected.",
    href: "/travel#where-to-go",
  },
  {
    id: "living",
    title: "Living here",
    description:
      "Residence, renting, banking, healthcare and the paperwork of settling in.",
    href: "/living",
  },
];

const LIVING_DOMAINS = new Set([
  "everyday-living",
  "healthcare",
  "business-registration",
]);

const TOKENS: ReadonlyArray<[BrandSectionId, ReadonlySet<string>]> = [
  [
    "visas",
    new Set([
      "visa",
      "visas",
      "registration",
      "customs",
      "passport",
      "documents",
      "insurance",
      "packing",
      "entry",
    ]),
  ],
  [
    "transport",
    new Set([
      "train",
      "trains",
      "metro",
      "taxi",
      "taxis",
      "flight",
      "flights",
      "airport",
      "arriving",
      "around",
      "transport",
      "bus",
      "driving",
    ]),
  ],
  [
    "planning",
    new Set([
      "sim",
      "esim",
      "esims",
      "internet",
      "eat",
      "food",
      "safe",
      "safety",
      "stay",
      "visit",
      "itinerary",
      "route",
      "season",
      "weather",
    ]),
  ],
  [
    "money",
    new Set([
      "money",
      "cash",
      "card",
      "cards",
      "atm",
      "atms",
      "cost",
      "costs",
      "budget",
      "prices",
      "currency",
      "som",
      "tipping",
    ]),
  ],
];

/** Classifies a guide by the words in its slug; order matters (a SIM card guide is planning, not money). */
export function sectionForPost(post: PublishedPostSummary): BrandSection {
  if (LIVING_DOMAINS.has(post.domain_slug ?? "")) return byId("living");
  const words = new Set(post.slug.toLowerCase().split("-"));
  for (const [id, tokens] of TOKENS) {
    if ([...words].some((word) => tokens.has(word))) return byId(id);
  }
  if (post.domain_slug === "immigration") return byId("visas");
  return byId("planning");
}

export type BrandSectionGroup = {
  section: BrandSection;
  posts: PublishedPostSummary[];
};

export function groupBySection(
  posts: PublishedPostSummary[],
): BrandSectionGroup[] {
  return BRAND_SECTIONS.map((section) => ({
    section,
    posts: posts.filter((post) => sectionForPost(post).id === section.id),
  }));
}

function byId(id: BrandSectionId): BrandSection {
  const section = BRAND_SECTIONS.find((candidate) => candidate.id === id);
  if (!section) throw new Error(`Unknown brand section: ${id}`);
  return section;
}
