# ADR 0015: Include light and dark appearance modes in the MVP

Date: 2026-08-01

Status: Accepted

Decision: D-009

## Context

The Phase 2 token foundation included an opt-in dark palette, but the MVP launch
scope and interaction contract were undecided. An appearance mode is not complete
unless it preserves contrast, semantic states, focus visibility, reflow, and motion
preferences rather than merely swapping backgrounds.

## Decision

The MVP includes light and dark appearance modes.

- The first visit follows `prefers-color-scheme`.
- A labelled toggle lets the person explicitly select light or dark mode.
- The explicit choice is stored locally on that device and overrides the system
  preference until changed.
- Components use semantic `light-dark()` tokens so status meaning and component
  APIs do not vary by appearance.
- Translucent materials become opaque under increased-contrast preferences.
- Both modes must pass the same WCAG 2.2 AA-oriented keyboard, focus, contrast,
  zoom/reflow, and screen-reader checks before launch.

## Consequences

- New components may not introduce light-only literal foreground or surface colors.
- Screenshots and visual-regression baselines must cover both modes.
- Appearance preference is non-sensitive local UI state and is not synchronized to
  an account in the MVP.
