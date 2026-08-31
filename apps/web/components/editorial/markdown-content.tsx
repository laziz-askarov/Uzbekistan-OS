import type { ReactNode } from "react";

function headingId(value: string) {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/[\s-]+/g, "-")
    .slice(0, 100);
}

function safeHref(value: string) {
  if (value.startsWith("/")) return value;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

function inlineMarkdown(value: string): ReactNode[] {
  const tokens: ReactNode[] = [];
  const pattern =
    /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*)/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(value)) !== null) {
    if (match.index > cursor) tokens.push(value.slice(cursor, match.index));
    if (match[2] && match[3]) {
      const href = safeHref(match[3]);
      tokens.push(
        href ? (
          <a href={href} key={`${match.index}-${href}`}>
            {match[2]}
          </a>
        ) : (
          match[2]
        ),
      );
    } else if (match[4]) {
      tokens.push(<strong key={match.index}>{match[4]}</strong>);
    } else if (match[5]) {
      tokens.push(<code key={match.index}>{match[5]}</code>);
    } else if (match[6]) {
      tokens.push(<em key={match.index}>{match[6]}</em>);
    }
    cursor = pattern.lastIndex;
  }
  if (cursor < value.length) tokens.push(value.slice(cursor));
  return tokens;
}

function isBlockStart(line: string) {
  return (
    /^#{1,4}\s/.test(line) ||
    /^>\s?/.test(line) ||
    /^[-*]\s/.test(line) ||
    /^\d+\.\s/.test(line) ||
    /^```/.test(line)
  );
}

export function MarkdownContent({ markdown }: { markdown: string }) {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^```([\w-]*)\s*$/);
    if (fence) {
      const content: string[] = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index])) {
        content.push(lines[index]);
        index += 1;
      }
      index += 1;
      blocks.push(
        <pre key={`code-${index}`}>
          <code data-language={fence[1] || undefined}>
            {content.join("\n")}
          </code>
        </pre>,
      );
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 1, 4);
      const id = headingId(heading[2]);
      const content = inlineMarkdown(heading[2]);
      blocks.push(
        level === 2 ? (
          <h2 id={id} key={`heading-${index}`}>
            {content}
          </h2>
        ) : level === 3 ? (
          <h3 id={id} key={`heading-${index}`}>
            {content}
          </h3>
        ) : (
          <h4 id={id} key={`heading-${index}`}>
            {content}
          </h4>
        ),
      );
      index += 1;
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quote: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quote.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(
        <blockquote key={`quote-${index}`}>
          {inlineMarkdown(quote.join(" "))}
        </blockquote>,
      );
      continue;
    }

    if (/^[-*]\s/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^[-*]\s/.test(lines[index])) {
        items.push(lines[index].replace(/^[-*]\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ul key={`list-${index}`}>
          {items.map((item, itemIndex) => (
            <li key={`${itemIndex}-${item}`}>{inlineMarkdown(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\.\s/.test(lines[index])) {
        items.push(lines[index].replace(/^\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ol key={`ordered-${index}`}>
          {items.map((item, itemIndex) => (
            <li key={`${itemIndex}-${item}`}>{inlineMarkdown(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !isBlockStart(lines[index])
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(
      <p key={`paragraph-${index}`}>{inlineMarkdown(paragraph.join(" "))}</p>,
    );
  }

  return <>{blocks}</>;
}
