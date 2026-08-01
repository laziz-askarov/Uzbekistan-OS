#!/usr/bin/env python3
"""Static acceptance checks for the Phase 2 accessible design-system baseline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, fragments: tuple[str, ...]) -> None:
    contents = (ROOT / path).read_text(encoding="utf-8")
    missing = [fragment for fragment in fragments if fragment not in contents]
    if missing:
        joined = ", ".join(repr(fragment) for fragment in missing)
        raise SystemExit(f"{path}: missing required design-system evidence: {joined}")


def main() -> None:
    require(
        "packages/design-system/src/components.tsx",
        (
            "<button",
            "<label",
            "aria-describedby",
            "aria-invalid",
            'tone === "error" ? "alert" : "status"',
            "aria-live",
            "export const Button",
            "export const TextField",
            "export const SelectField",
            "export function Card",
            "export function Alert",
            "export function Badge",
            "export function Stack",
        ),
    )
    require(
        "packages/design-system/components.css",
        (
            "min-height: var(--control-comfortable-size)",
            ":focus-visible",
            "@media (prefers-reduced-motion: reduce)",
        ),
    )
    require(
        "packages/design-system/tokens.css",
        (
            'color-scheme: light dark',
            '[data-theme="light"]',
            '[data-theme="dark"]',
            "light-dark(",
            "--control-min-size: 2.75rem",
        ),
    )
    require("packages/design-system/tailwind.css", ("@theme inline",))
    require(
        "apps/web/app/design-system/page.tsx",
        ("<Button", "<TextField", "<SelectField", "<Card", "<Alert", "<Badge", "<Stack"),
    )
    require(
        "apps/web/app/design-system/theme-toggle.tsx",
        (
            'aria-label={`Switch to ${nextTheme} mode`}',
            'aria-pressed={theme === "dark"}',
            'window.matchMedia("(prefers-color-scheme: dark)")',
            "window.localStorage.setItem",
            "document.documentElement.dataset.theme",
        ),
    )
    print("Design-system acceptance checks passed.")


if __name__ == "__main__":
    main()
