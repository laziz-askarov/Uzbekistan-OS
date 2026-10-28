import type { CSSProperties } from "react";
import { parseMosaic } from "@/lib/anor-mosaic";
import { ANOR_MOSAIC_SVG } from "@/lib/anor-mosaic.svg";
import styles from "./anor-mosaic.module.css";

const mosaic = parseMosaic(ANOR_MOSAIC_SVG);
const body = mosaic.tiles[0];

type AnorMosaicProps = {
  className?: string;
  /** Lay the tiles one at a time on first paint and let light cross them at rest. */
  animate?: boolean;
};

/**
 * The Anor mark as live SVG: every tessera is its own element, in the order
 * the mark was cut, so the page can lay them one by one.
 */
export function AnorMosaic({ className, animate = true }: AnorMosaicProps) {
  const classes = [styles.mosaic, animate ? styles.live : "", className ?? ""]
    .filter(Boolean)
    .join(" ");
  return (
    <svg
      className={classes}
      viewBox={mosaic.viewBox}
      role="img"
      aria-label="Anor, the Uzbekistan OS mark: a pomegranate laid in mosaic"
    >
      {mosaic.tiles.map((tile, index) => {
        const style = { "--i": index } as CSSProperties;
        return tile.kind === "circle" ? (
          <circle
            key={index}
            className={styles.tile}
            cx={tile.cx}
            cy={tile.cy}
            r={tile.r}
            fill={tile.fill}
            style={style}
          />
        ) : (
          <path
            key={index}
            className={styles.tile}
            d={tile.d}
            fill={tile.fill}
            style={style}
          />
        );
      })}
      {animate && body.kind === "circle" ? (
        <g aria-hidden="true" clipPath="url(#anor-body)">
          <defs>
            <clipPath id="anor-body">
              <circle cx={body.cx} cy={body.cy} r={body.r} />
            </clipPath>
            <linearGradient id="anor-glint" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stopColor="#FFFFFF" stopOpacity="0" />
              <stop offset="0.5" stopColor="#FFFFFF" stopOpacity="0.32" />
              <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
            </linearGradient>
          </defs>
          <rect
            className={styles.glint}
            x="-40"
            y="0"
            width="120"
            height="256"
            fill="url(#anor-glint)"
            transform="skewX(-18)"
          />
        </g>
      ) : null}
    </svg>
  );
}
