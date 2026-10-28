type JsonLdProps = {
  data: Record<string, unknown>;
};

/**
 * Serialize structured data for search and answer engines. Closing-tag
 * characters are escaped so post titles or bios can never end the script.
 */
export function JsonLd({ data }: JsonLdProps) {
  const json = JSON.stringify(data).replace(/</g, "\\u003c");
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: json }}
    />
  );
}
