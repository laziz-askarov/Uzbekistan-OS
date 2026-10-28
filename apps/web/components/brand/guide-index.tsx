"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import type { BrandSectionId } from "@/lib/brand-sections";
import styles from "./guide-index.module.css";

export type IndexGuide = {
  slug: string;
  href: string;
  title: string;
  verified: string;
  verifiedAt: string;
  image: string | null;
  alt: string;
};

export type IndexGroup = {
  id: BrandSectionId;
  title: string;
  description: string;
  href: string;
  count: string;
  guides: IndexGuide[];
};

const PREVIEW_WIDTH = 320;
const PREVIEW_HEIGHT = 240;

/**
 * The guide index: section rows with their guides. With a fine pointer, the
 * hovered guide's photograph floats beside the pointer; on touch and small
 * screens every guide shows its photograph inline instead.
 */
export function GuideIndex({ groups }: { groups: IndexGroup[] }) {
  const [active, setActive] = useState<IndexGuide | null>(null);
  const preview = useRef<HTMLDivElement>(null);

  const place = useCallback((x: number, y: number) => {
    const el = preview.current;
    if (!el) return;
    // Sit on the emptier side of the pointer: left of it in the guides column.
    const side = x > window.innerWidth * 0.55 ? x - PREVIEW_WIDTH - 28 : x + 28;
    const left = Math.min(
      Math.max(16, side),
      window.innerWidth - PREVIEW_WIDTH - 16,
    );
    const top = Math.min(
      Math.max(16, y - PREVIEW_HEIGHT / 2),
      window.innerHeight - PREVIEW_HEIGHT - 16,
    );
    el.style.translate = `${Math.round(left)}px ${Math.round(top)}px`;
  }, []);

  const show = useCallback(
    (guide: IndexGuide, target: HTMLElement) => {
      if (!guide.image) return;
      const rect = target.getBoundingClientRect();
      place(rect.right, rect.top + rect.height / 2);
      setActive(guide);
    },
    [place],
  );

  return (
    <div
      className={styles.index}
      onPointerMove={(event) => {
        if (event.pointerType === "mouse") place(event.clientX, event.clientY);
      }}
      onPointerLeave={() => setActive(null)}
    >
      <ul className={styles.rows}>
        {groups.map((group) => (
          <li className={styles.row} data-section={group.id} key={group.id}>
            <div className={styles.rowHead}>
              <h3>
                <Link href={group.href}>
                  <i className={styles.tile} aria-hidden="true" />
                  {group.title}
                </Link>
              </h3>
              <span className={styles.count}>{group.count}</span>
              <p>{group.description}</p>
            </div>
            <ul className={styles.guides}>
              {group.guides.map((guide) => (
                <li key={guide.href}>
                  <Link
                    href={guide.href}
                    data-image={guide.image ?? undefined}
                    onPointerEnter={(event) => {
                      if (event.pointerType === "mouse")
                        show(guide, event.currentTarget);
                    }}
                    onFocus={(event) => show(guide, event.currentTarget)}
                    onBlur={() => setActive(null)}
                  >
                    {guide.image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        className={styles.thumb}
                        src={guide.image}
                        alt=""
                        width={96}
                        height={72}
                        loading="lazy"
                        decoding="async"
                      />
                    ) : (
                      <span className={styles.thumb} aria-hidden="true" />
                    )}
                    <span className={styles.guideTitle}>{guide.title}</span>
                    <time dateTime={guide.verifiedAt}>{guide.verified}</time>
                  </Link>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      <div
        className={styles.preview}
        ref={preview}
        aria-hidden="true"
        data-show={active ? "" : undefined}
      >
        {active?.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={active.image}
            alt=""
            width={PREVIEW_WIDTH}
            height={PREVIEW_HEIGHT}
            decoding="async"
          />
        ) : null}
      </div>
    </div>
  );
}
