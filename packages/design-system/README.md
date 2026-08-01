# Uzbekistan OS design system

The design system uses `tokens.css` as its framework-neutral source of truth.
`tailwind.css` maps those source tokens into Tailwind v4 theme names without
making Tailwind a runtime dependency. `components.css` and `src/` provide the
accessible React primitives used by the web application.

## Accessibility contract

- Interactive controls use native HTML elements and maintain a minimum 44px
  target size.
- Every field has a programmatic label. Hints and validation errors are wired
  through `aria-describedby`; invalid fields use `aria-invalid`.
- Alerts use polite status announcements unless the error requires an
  assertive alert.
- Keyboard focus is always visible, and component motion is removed when the
  user requests reduced motion.
- Light and dark modes follow the system preference by default and support an
  explicit locally persisted override under accepted decision D-009. Both modes
  share the same semantic tokens and accessibility contract.

The live component catalogue is available at `/design-system` in the web app.

## Visual language

The visual language is informed by Apple's Human Interface Guidelines while
remaining an original Uzbekistan OS system:

- Content hierarchy comes before decoration, with large titles and a restrained
  type scale.
- Platform-native typography and familiar native controls reduce learning cost.
- Rounded geometry, semantic color, and gentle feedback make state legible without
  relying on color alone.
- Translucent material is reserved for navigation and floating utility layers;
  content surfaces remain calm and opaque.
- Layouts preserve context from touch-sized mobile screens through wide desktop
  views, with explicit reduced-motion and increased-contrast behavior.
