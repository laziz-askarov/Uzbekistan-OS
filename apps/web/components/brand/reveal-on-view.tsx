"use client";

import { useEffect, useRef, type ReactNode } from "react";

type RevealOnViewProps = {
  children: ReactNode;
  className?: string;
};

/**
 * Marks its box with data-reveal="pending" after mount and "go" once a third
 * of it is on screen, so CSS can start an animation when the visitor arrives.
 * Server HTML carries no attribute, so the content is complete without JS.
 */
export function RevealOnView({ children, className }: RevealOnViewProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (
      !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }
    el.dataset.reveal = "pending";
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          el.dataset.reveal = "go";
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
