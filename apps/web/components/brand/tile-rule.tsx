import type { BrandSectionId } from "@/lib/brand-sections";
import styles from "./tile-rule.module.css";

const TILES = 24;
const COLOURED: Record<BrandSectionId, number> = {
  visas: 6,
  money: 7,
  transport: 9,
  planning: 4,
  living: 5,
};

/** The kit's divider: a row of neutral tiles with one in the next section's colour. */
export function TileRule({ section }: { section: BrandSectionId }) {
  return (
    <div className={styles.rule} data-section={section} aria-hidden="true">
      {Array.from({ length: TILES }, (_, index) => (
        <i key={index} data-hl={index === COLOURED[section] ? "" : undefined} />
      ))}
    </div>
  );
}
