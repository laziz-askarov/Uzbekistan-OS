# Uzbekistan OS web design system (brand kit, October 2026)

Planning artifact for the brand-kit redesign of the public site. The kit lives at
`Uzbekistan-OS-brand-kit/` (owner-supplied, 2026-10-28); its tokens, logo rules, voice and
component notes are the authority. This file records the concept and the decisions that the
kit leaves open, so later passes stay consistent. Preview route: `/preview`.

## Brief

- Subject: Uzbekistan OS by Kebab Travel, a verified guide to travelling in and living in
  Uzbekistan. Thirteen English guides are published through the API today.
- Audience: travellers from the US and Europe planning a first trip, plus people staying longer.
- Job: be read and cited, then turn readers into email trip inquiries for Kebab Travel.
- Assets: Anor logo set, favicons, tile motif, section icons, OG templates, tokens, Inter.
- Constraints: layouts neutral, roughly 90% neutral to 10% highlight; Inter for everything;
  pomegranate is the one primary button per screen; turquoise, saffron and cobalt are fills
  only; the mark is never shown without its seeds; no payments or bookings on the site.

## Concept card

```
Idea:        A calm plaster wall with one mosaic panel. The page is neutral; the Anor is the
             only place colour lives, and a single tessera travels to mark where you are.
Metaphor:    Tashkent's mosaic walls and metro stations: smalt tiles set one at a time in grout.
Signature:   The hero mosaic lays itself tile by tile on first paint (310 tesserae, about
             1.2 s, in the order the mark was cut), then light crosses the tiles slowly at rest.
Emotion:     Calm, certain, handmade. "Someone here has checked this."
Motion verb: Lay a tile. Things settle into their place with one short, firm ease and never
             bounce. Hovers set a tile next to the thing you point at.
Screenshot:  The hero: the display headline on the left, the mosaic half laid on the right.
```

Concepts considered: (A) the mosaic wall, from the identity itself; (B) the logbook of checks,
from the "Last checked" voice rule; (C) the metro map, from Tashkent. A scored 4/5/5/1
(originality, fit, feasibility, portability), B 3/4/5/3, C 4/3/4/3. A chosen because the
kit already states it ("a calm white wall with one mosaic panel"). From B we keep the
dateline under the hero and the verified date on every card.

## System

Palette (kit tokens, light theme committed; dark theme is in the kit but not built yet):
paper #F8F6F1 ground, surface #FFFFFF, sunken #F0ECE4, line #E6E0D5, ink #1F1C18, muted
#5F5850, pomegranate #C8102E, cobalt #8AB4FF, saffron #FFC233, turquoise #55D6E4, and the
section text shades (#2A4FBF, #7A4E00, #0A6B75, #A50D26). Grout #E4D5B4 appears only inside
the mark and the tile rule.

Type: Inter, every role. Display 800, clamp(40px, 2.4vw + 24px, 60px), leading 1.02, tracking
-0.025em. H2 28/34 700 -0.4px. H3 20/28 600. Body 17/27. Small 14/20. Label 12 700 caps,
+0.6px, only inside section tags. Tabular numerals for counts and dates.

Grid: 12 columns, 24px gutter, 1200px max. Text hangs from column 1; asides and the mosaic
hang from column 8. Section rhythm: hero airy, index normal, route airy, cards normal, service
tight inside a sunken band, footer normal.

Shape: 14px cards and image frames, 8px buttons and tags, 3px tiles.

Motion: one ease, cubic-bezier(0.2, 0.7, 0.2, 1). Hover 320 ms. Mosaic lay 420 ms per tile,
3 ms stagger. Glint 2.4 s every 9 s. No loader, no page curtain, no smooth-scroll library: a
guide site earns craft in type and layout, not theatre. Reduced motion: the mosaic is
complete on first paint, the glint is off, hovers keep their colour and tile without movement.

Hover treatments, one per role:

- Nav links: the section tile appears beside the label (the kit's rule); current page keeps it.
- Primary and secondary buttons: a fill slides in from the left (deep pomegranate, or sunken).
- Cards and index rows: the border turns ink and the coloured tile in the tile row steps one
  place to the right.
- Inline links: underline at rest, thicker on hover.

Sections and colours (kit): Visas and documents cobalt, Money saffron, Getting around
turquoise, Living here pomegranate. Planning guides (routes, seasons, stays, food, safety,
SIM) carry the ink tile: a neutral section, because the kit reserves colour for those four.

## Composition (each layout family once)

```
Header   [anor-horizontal 40px]                 Travel guides  Living  About  [Plan my trip]
Hero     ┌───────────────── cols 1-7 ─────────────────┐ ┌──── cols 8-12 ────┐
         │ Everything you need to know about          │ │                   │
         │ Uzbekistan.                                │ │   Anor mosaic     │
         │ deck, two lines                            │ │   (laying itself) │
         │ [Start with the first-trip guide] How we   │ │                   │
         │ Last checked 28 October 2026. 13 guides.   │ └───────────────────┘
Tile rule (cobalt)
Index    Visas and documents   3 guides   Visa requirements · Tourist registration · Packing
         Money                 2 guides   ...
         Getting around        2 guides   ...
         Planning the trip     5 guides   ...
         Living here           4 sections ...
Tile rule (saffron)
Route    ┌──── photo cols 1-7 ────┐  1 Tashkent  one to two days
         │ Tashkent at dusk       │  2 Samarkand two days
         └────────────────────────┘  3 Bukhara ... 4 Khiva ...
Tile rule (turquoise)
Latest   [card] [card] [card]   (section tag, title, verified date, tile row)
Service  sunken band: seed cluster, "Want the trip planned for you?", [Plan my trip]
Footer   logo, columns, policy links, "Last checked" line
```

Genericness check: a generic answer here would be a cream page with a serif display and a
clay accent, three feature cards and an eyebrow over every heading. This system uses the
kit's Inter-only type, a neutral ground with colour confined to the mark and the tiles, an
index list instead of cards for the sections, numbers only where the content is a sequence
(the route), and labels only inside section tags.

## Still open

- The "Planning the trip" pin icon is not in the kit; the other four icons are. Ask the kit's
  designer for a fifth icon in the same filled style, or drop the neutral section's icon.

- Dark theme from the kit tokens.
- Replace the Tashkent skyline with the owner's own photos (everyday scenes, warm light).
- OG image from `05-social-templates/og-image-template.svg` once the route is approved.
