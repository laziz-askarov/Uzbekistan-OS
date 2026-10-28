export const SITE_NAME = "Uzbekistan OS";
export const OPERATOR_NAME = "Kebab Travel";
export const SITE_LOCKUP = `${SITE_NAME} by ${OPERATOR_NAME}`;
export const SITE_TAGLINE = "The verified guide to travelling in Uzbekistan";
export const SITE_DESCRIPTION =
  "Visa rules, registration, trains, money, SIM cards, safety and itineraries for travellers from the US and Europe. Every guide shows when it was last verified and which official source says so.";
export const CONTACT_EMAIL = "info@uzbekistanos.com";
export const OPERATOR_CITY = "Tashkent";
export const OPERATOR_COUNTRY = "UZ";

export type NavigationItem = {
  href: string;
  label: string;
  emphasis?: boolean;
};

export const PRIMARY_NAVIGATION: readonly NavigationItem[] = [
  { href: "/travel", label: "Travel guides" },
  { href: "/living", label: "Living" },
  { href: "/about", label: "About" },
  { href: "/trips", label: "Plan my trip", emphasis: true },
];

export const FOOTER_NAVIGATION: readonly NavigationItem[] = [
  { href: "/travel", label: "Travel guides" },
  { href: "/living", label: "Living in Uzbekistan" },
  { href: "/blog", label: "All guides" },
  { href: "/trips", label: "Plan my trip" },
  { href: "/about", label: "About" },
  { href: "/about#methodology", label: "How we verify" },
];

export const POLICY_NAVIGATION: readonly NavigationItem[] = [
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/terms", label: "Terms of Use" },
  { href: "/blog/rss.xml", label: "RSS" },
  { href: "/llms.txt", label: "LLM index" },
];
