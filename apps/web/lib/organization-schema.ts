import {
  CONTACT_EMAIL,
  OPERATOR_CITY,
  OPERATOR_COUNTRY,
  OPERATOR_NAME,
  SITE_DESCRIPTION,
  SITE_NAME,
} from "@/lib/site";

export function organizationId(siteUrl: string) {
  return `${siteUrl}/#organization`;
}

export function organizationGraph(siteUrl: string) {
  const organization = {
    "@type": "Organization",
    "@id": organizationId(siteUrl),
    name: OPERATOR_NAME,
    url: `${siteUrl}/about`,
    email: CONTACT_EMAIL,
    logo: `${siteUrl}/opengraph-image`,
    address: {
      "@type": "PostalAddress",
      addressLocality: OPERATOR_CITY,
      addressCountry: OPERATOR_COUNTRY,
    },
    description: `${OPERATOR_NAME} is the Tashkent-based travel company that publishes ${SITE_NAME} and plans trips to Uzbekistan.`,
  };
  const website = {
    "@type": "WebSite",
    "@id": `${siteUrl}/#website`,
    name: SITE_NAME,
    url: siteUrl,
    description: SITE_DESCRIPTION,
    inLanguage: "en",
    publisher: { "@id": organization["@id"] },
  };
  return {
    "@context": "https://schema.org",
    "@graph": [organization, website],
  };
}
