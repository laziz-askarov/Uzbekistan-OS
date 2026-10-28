/**
 * Reads the Anor mosaic SVG from the brand kit into a list of tesserae, in
 * the order the mark was cut, so the page can lay them one at a time.
 */
export type MosaicTile =
  | { kind: "circle"; cx: number; cy: number; r: number; fill: string }
  | { kind: "path"; d: string; fill: string };

export type Mosaic = {
  viewBox: string;
  tiles: MosaicTile[];
};

const ELEMENT = /<(circle|path)\b([^>]*)\/>/g;

function attribute(attributes: string, name: string): string {
  const match = attributes.match(new RegExp(`\\b${name}="([^"]*)"`));
  if (!match) throw new Error(`Mosaic element is missing ${name}`);
  return match[1];
}

export function parseMosaic(svg: string): Mosaic {
  const viewBox = svg.match(/viewBox="([^"]+)"/)?.[1];
  if (!viewBox) throw new Error("Mosaic SVG has no viewBox");
  const tiles: MosaicTile[] = [];
  for (const [, kind, attributes] of svg.matchAll(ELEMENT)) {
    const fill = attribute(attributes, "fill").toUpperCase();
    if (kind === "circle") {
      tiles.push({
        kind: "circle",
        cx: Number(attribute(attributes, "cx")),
        cy: Number(attribute(attributes, "cy")),
        r: Number(attribute(attributes, "r")),
        fill,
      });
    } else {
      tiles.push({ kind: "path", d: attribute(attributes, "d"), fill });
    }
  }
  return { viewBox, tiles };
}
