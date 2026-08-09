# Uzbekistan OS visual design language

Status: MVP design direction
Last updated: 2026-08-09
Reference inspiration: [Lumos Figma landing-page frame](https://www.figma.com/design/2XAZzNlOfcDAkgQx2vCXLZ/Lumos-Figma-File--Community-?node-id=2409-213), adapted for Uzbekistan OS
Applies to: public web, guided workflows, grounded answers, knowledge pages,
authentication, administration, review, and the design-system catalogue

## Internal visa workspace reference

The signed-in experience lives at `/chat` as a utility-mode workspace. It
recreates the supplied internal chat design with a 260px conversation sidebar,
compact product header, structured assistant responses, collapsible visa
sections, official-source links, and a persistent message composer.

- The public landing page remains editorial; the internal workspace is calm,
  dense enough for procedural work, and optimized for long-form reading.
- The workspace uses the same near-black, white, gray, blue, and green palette
  as the landing page, with 12–18px rounded controls and cards.
- User messages use a dark speech bubble. Assistant answers use structured
  white cards so eligibility, documents, steps, timing, fees, restrictions, and
  sources are scannable.
- Mobile navigation becomes an accessible off-canvas conversation menu.
- Until secure authentication and persistence are wired, the route remains a
  preview account surface and does not collect or save personal data.
- Autonomous application, appointment booking, payment, and document-upload
  actions are intentionally excluded from this MVP surface.

### Grounded GPT behavior

Live chat turns use a server-side GPT model through the OpenAI API. The
model never chooses legal workflow state or source eligibility. Deterministic
application code first maps each request to a visa workflow, supplies only the
reviewed evidence allowed for that workflow, requires a typed response with a
validated traveler profile and source identifiers, and rejects output whose
profile fields or citations fall outside the selected workflow. Unsupported
output degrades to a safe insufficiency response.

The visa knowledge base retains the 13 supplied Word documents as immutable
source snapshots. An ingestion script extracts paragraphs and tables into 52
searchable excerpts and records each source filename, topic, official service
URL, import date, and SHA-256 checksum. Retrieval combines the selected workflow
with terms from the complete user conversation, includes evidence from every
required topic, limits duplicate excerpts from one document, and sends only the
best matching excerpts to GPT. This keeps visa-type selection grounded in the
actual supplied material while preserving source lineage.

Intake behaves like a helpful conversation rather than a form. GPT acknowledges
the detail just provided and asks one short question at a time, never repeating
facts already collected. A separate typed context pass scans the complete thread,
uses assistant questions only to interpret short user replies, and extracts only
explicit user facts. Application code then computes the remaining required fields
deterministically, so a confirmed detail such as “US citizen” cannot be requested
again. It also selects the next question from the first missing field instead of
allowing generated text to choose an already-completed field. A compact progress
card shows the confirmed profile
facts without exposing the full plan early. When every required field for the
selected workflow is present, the interface switches automatically to a
personalized workflow with the user's details, requirements, documents,
application steps, timing, fees, arrival obligations, and reviewed sources when
supported by evidence.

New chat sessions begin empty. No sample e-visa request or generated workflow is
included in API history, so an unrelated tourism question cannot inherit a visa
type from demonstration content.

The initial workflow set covers route discovery, visa-free entry, electronic
and consular visas, business, employment, study, private or family visits,
residence permits, arrival registration, and overstay or exit questions.

## 1. Purpose

Uzbekistan OS should feel like the clearest, most trustworthy way to navigate a
complex country process. The interface combines two complementary influences:

1. Apple's Human Interface Guidelines supply the interaction foundation:
   hierarchy, platform familiarity, legibility, clear state, generous targets,
   progressive disclosure, and respectful motion.
2. Wolverine Worldwide supplies the editorial attitude: oversized typography,
   confident negative space, asymmetric grid composition, full-bleed human
   imagery, near-black and white contrast, rounded cinematic frames, and
   restrained scroll-driven reveals.

This is an adaptation, not a replica. Do not copy Wolverine Worldwide's logo,
brand assets, photography, text, source code, or proprietary typeface. The
result must be recognizably Uzbekistan OS and must prioritize civic clarity over
brand spectacle.

## 2. Design thesis

**Editorial confidence for civic certainty.**

The product should feel calm, current, and capable. Important information is
large and direct. Supporting information is precise and quiet. Official evidence
is visible. Complex procedures become a clear sequence of decisions rather than
a wall of institutional language.

The visual system has two operating modes:

- **Editorial mode** is used on the home page, domain introductions, campaign
  moments, and major workflow entry points. It may use cinematic media,
  oversized display type, offset grids, and expressive reveals.
- **Utility mode** is used inside guided flows, search, answers, checklists,
  account surfaces, admin tools, and review tools. It uses the same tokens but
  favors stable layouts, readable measures, predictable controls, and minimal
  motion.

Editorial mode invites. Utility mode helps someone finish.

## 3. Non-negotiable principles

### 3.1 Trust before novelty

- Show the official source, retrieval date, applicability, and review status near
  procedural claims.
- Never use visual polish to conceal missing evidence, uncertainty, or an error.
- Use localized safe insufficiency when evidence is incomplete.
- Keep administrative and publication states explicit in text, not color alone.

### 3.2 One clear next action

- Every screen has one primary task.
- Primary actions use direct verbs: `Check eligibility`, `Continue`, `Review
sources`, `Save checklist`.
- Secondary actions are visually quieter.
- Avoid dashboards of equal-weight cards when a guided sequence is more useful.

### 3.3 Progressive disclosure

- Ask only for information needed for the current decision.
- Reveal explanations, exceptions, and evidence at the point of relevance.
- Preserve progress and make the current step visible.
- Never hide legally important conditions behind hover-only interaction.

### 3.4 Human, not touristic

- Portray contemporary life in Uzbekistan: people arriving, working, studying,
  running businesses, receiving care, and handling everyday tasks.
- Avoid decorative nationalism, generic Silk Road imagery, staged government
  handshakes, or an overreliance on monuments.
- Use architecture and landscape as context, not as a substitute for people.

### 3.5 Accessible in every mode

- Meet WCAG 2.2 AA-oriented requirements in light and dark themes.
- Preserve keyboard order, visible focus, semantic structure, zoom, and reflow.
- Respect `prefers-reduced-motion` and increased-contrast preferences.
- English, Uzbek, and Russian are equal product languages.

## 4. Visual character

Uzbekistan OS is:

- confident, not loud;
- modern, not fashionable for its own sake;
- warm, not playful;
- official-source grounded, not institutional;
- spacious, not empty;
- cinematic at entry points, efficient during tasks;
- rounded and tactile, not glossy;
- precise, not dense.

## 5. Source-inspired characteristics

The reference site uses a strong editorial system. The relevant characteristics
to adapt are:

- a 12-column desktop grid;
- approximately 20px gutters;
- compact mobile margins and generous desktop margins;
- large display text with tight leading and negative tracking;
- short headlines broken into deliberate lines;
- black, white, and neutral gray as the dominant palette;
- small areas of imagery placed around or behind oversized typography;
- large cinematic image or video fields inside rounded outer frames;
- asymmetric content placement instead of centered card grids everywhere;
- floating or condensed navigation over immersive media;
- arrow-led calls to action with subtle horizontal movement;
- image scale, opacity, and upward reveals using expressive easing;
- 0.4–1 second editorial transitions, with faster control feedback;
- generous vertical separation between narrative chapters.

Use these as compositional ideas. Do not reproduce the reference page section by
section.

## 6. Typography

### 6.1 Font family

Do not use the reference site's proprietary `ABCDiatype` font without an
appropriate license. Uzbekistan OS uses a platform-native and multilingual stack:

```css
--font-sans:
  -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Inter,
  "Noto Sans", Arial, sans-serif;

--font-display:
  -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Inter,
  "Noto Sans", Arial, sans-serif;
```

Every selected font must include robust Latin and Cyrillic coverage. Test Uzbek
apostrophe variants and Russian text before release.

### 6.2 Type scale

```css
--type-label: clamp(0.75rem, 0.72rem + 0.12vw, 0.8125rem);
--type-body-sm: clamp(0.875rem, 0.84rem + 0.16vw, 0.9375rem);
--type-body: clamp(1rem, 0.96rem + 0.2vw, 1.125rem);
--type-body-lg: clamp(1.125rem, 1rem + 0.6vw, 1.5rem);
--type-heading-sm: clamp(1.5rem, 1.2rem + 1.5vw, 2.5rem);
--type-heading: clamp(2rem, 1.35rem + 3.25vw, 4.25rem);
--type-display: clamp(3.25rem, 1.7rem + 7.75vw, 8rem);
--type-display-xl: clamp(4rem, 1.8rem + 11vw, 10rem);
```

### 6.3 Type roles

| Role          |  Weight | Line height |         Tracking | Use                      |
| ------------- | ------: | ----------: | ---------------: | ------------------------ |
| Display XL    | 700–760 |    0.82–0.9 |       `-0.065em` | Home or domain hero only |
| Display       | 700–760 |   0.88–0.96 |       `-0.055em` | Workflow entry headlines |
| Heading       | 680–740 |   0.98–1.05 |        `-0.04em` | Section titles           |
| Heading small | 650–720 |   1.05–1.12 |       `-0.025em` | Card and step titles     |
| Body large    | 500–680 |    1.2–1.35 |       `-0.015em` | Editorial statements     |
| Body          | 400–520 |    1.45–1.6 | `-0.01em` to `0` | Procedural copy          |
| Label         | 600–720 |    1.2–1.35 |  `0` to `0.04em` | Metadata and controls    |

### 6.4 Typography rules

- Use sentence case by default.
- Limit all-caps treatment to short Latin metadata labels. Do not force all-caps
  across Uzbek or Russian text.
- Display headlines should contain 2–8 words and no more than three deliberate
  lines on desktop.
- Use `text-wrap: balance` for editorial headings and `text-wrap: pretty` for
  body text.
- Keep procedural body text between 45 and 75 characters per line.
- Do not apply display typography to forms, alerts, citations, tables, or error
  messages.
- Never reduce body text below 14px or control text below 13px.
- Use tabular numbers for prices, dates, durations, and dashboard metrics.

## 7. Color

### 7.1 Palette strategy

The reference's near-black and white contrast becomes the neutral foundation.
Uzbekistan OS blue remains the civic action color. Turquoise is a secondary
regional accent and must not compete with primary actions.

```css
:root {
  --uos-black: #0b0d0f;
  --uos-black-deep: #050607;
  --uos-white: #ffffff;
  --uos-paper: #f5f6f8;
  --uos-paper-warm: #f3f2ed;
  --uos-gray-100: #eceef1;
  --uos-gray-300: #c9cdd3;
  --uos-gray-500: #777d87;
  --uos-gray-700: #454a52;

  --uos-blue: #0668d7;
  --uos-blue-hover: #055bbd;
  --uos-blue-soft: #e7f1ff;
  --uos-turquoise: #0c8f91;
  --uos-turquoise-soft: #e1f5f3;

  --uos-success: #16794a;
  --uos-warning: #9a5a00;
  --uos-error: #c72c3b;
  --uos-info: #007eaa;
}
```

### 7.2 Color distribution

- Neutral black, white, or paper tones should occupy approximately 80–90% of a
  public screen.
- Primary blue should occupy less than 10% and signal actions, links, focus, and
  active progress.
- Turquoise is reserved for supporting emphasis, destination context, and
  selected editorial moments.
- Status colors communicate meaning only when paired with an icon and text.

### 7.3 Dark mode

Dark mode is a first-class MVP mode, not an inverted afterthought.

- Use `#0f1012` for the base background and `#1c1d20` for opaque surfaces.
- Use pure black only for immersive media framing or the footer.
- Keep primary text near `#f5f6f8` and secondary text near `#b6bac3`.
- Raise blue luminance in dark mode to preserve contrast.
- Avoid large areas of saturated blue.
- Decorative imagery must retain enough overlay contrast for text.
- Translucent material becomes opaque when increased contrast is requested.

## 8. Grid and layout

### 8.1 Responsive grid

```css
--layout-max: 90rem;
--layout-reading: 46rem;
--layout-form: 40rem;
--grid-columns: 12;
--grid-gutter: clamp(0.75rem, 0.5rem + 1vw, 1.25rem);
--page-margin: clamp(0.75rem, 0.25rem + 3vw, 3rem);
```

- Mobile: 4 conceptual columns, 12px page margin, 12px gutter.
- Tablet: 8 conceptual columns, 24px page margin, 16px gutter.
- Desktop: 12 columns, 32–48px page margin, 20px gutter.
- Wide screens: cap primary content at 1440px and center it.
- Reading content remains between 640px and 736px wide.

### 8.2 Section spacing

```css
--section-gap-sm: clamp(3.5rem, 2.7rem + 4vw, 5.5rem);
--section-gap: clamp(5.5rem, 4.1rem + 7vw, 9.5rem);
--section-gap-lg: clamp(8rem, 6rem + 10vw, 13rem);
```

- Editorial chapters use `--section-gap` or `--section-gap-lg`.
- Utility screens use 24–64px vertical groups.
- Keep related label, value, hint, and error spacing within 4–12px.
- Do not use large editorial whitespace inside a multi-step task.

### 8.3 Composition patterns

Use these patterns deliberately:

1. **Cinematic hero:** inset full-bleed media, 16–24px outer radius, white or
   near-black headline over a controlled contrast area.
2. **Offset statement:** large copy spans columns 6–11 while columns 1–5 remain
   quiet or carry a small label.
3. **Headline galaxy:** oversized text with a small number of supporting images
   placed around it. Use only for domain discovery, never procedural results.
4. **Split evidence chapter:** headline and summary on the left; source list,
   deadlines, or checklist on the right.
5. **Editorial rail:** horizontally scrollable cards with one partially visible
   next item and explicit previous/next controls.
6. **Utility column:** centered 640px flow column with persistent progress and a
   stable bottom action area on narrow screens.
7. **Admin workbench:** full-width grid with a navigation rail, filters, data
   table, and a details panel. Do not force editorial asymmetry into operations.

### 8.4 Alignment

- Prefer strong left alignment.
- Center only a short onboarding or empty state.
- Allow headlines to cross columns, but keep form controls and evidence aligned.
- Avoid equal three-card rows as the default home-page composition.
- Use negative space to create hierarchy, not to reduce information density
  artificially.

## 9. Shape, border, and depth

```css
--radius-xs: 0.375rem;
--radius-sm: 0.625rem;
--radius-control: 0.875rem;
--radius-card: 1.25rem;
--radius-panel: 1.5rem;
--radius-hero: clamp(1rem, 0.8rem + 1vw, 1.5rem);
--radius-pill: 999px;
```

- Use 14px rounded controls and 20–24px content panels.
- Large media fields use 16–24px radii.
- Use thin, low-contrast borders on utility surfaces.
- Prefer tonal separation to heavy shadows.
- Reserve floating shadows for menus, sheets, command bars, and sticky actions.
- Avoid glass effects behind long-form content.

## 10. Images and media

### 10.1 Art direction

Images should communicate a real step in someone's journey:

- arriving at an airport or railway station;
- speaking with a hotel or registration representative;
- studying or working in a contemporary environment;
- using public or private healthcare;
- opening a small business;
- renting a home or navigating a neighborhood;
- reading an official form without exposing personal data.

Prefer candid documentary framing, natural light, believable environments, and
clear human action. Build an original licensed Uzbekistan OS library.

### 10.2 Composition

- Use cinematic landscape media between 16:9 and 3:2 for heroes.
- Use 4:5 or 3:4 for people and story cards.
- Use 1:1 sparingly for icons, avatars, or the headline-galaxy treatment.
- Crop decisively with `object-fit: cover` and set an intentional focal point.
- Keep faces, hands, and critical context clear of text overlays.
- Apply a 20–45% dark overlay only when needed for readable text.
- Avoid gradients that obscure evidence or official-document content.

### 10.3 Video

Autoplay video may appear only on a marketing or domain-entry hero.

- Must be muted, looping, inline, and shorter than 12 seconds.
- Must provide a static poster and a user-visible pause control.
- Must not convey information unavailable in text.
- Must not autoplay when reduced motion or data-saving preferences apply.
- Target less than 3 MB for the initial mobile asset when practical.
- Guided flows, answer screens, knowledge pages, and admin screens use no
  decorative autoplay video.

### 10.4 Content restrictions

- Never use copyrighted reference-site images in Uzbekistan OS.
- Never use government seals as decorative endorsement.
- Never expose passports, visas, IDs, medical records, addresses, or account
  details in photography.
- Never use screenshots of official documents as background texture.

## 11. Motion

Motion should make hierarchy and state easier to understand. The reference uses
long, expressive easing for editorial reveals; Uzbekistan OS limits that
language to low-risk discovery surfaces.

### 11.1 Timing

```css
--motion-instant: 100ms;
--motion-fast: 140ms;
--motion-standard: 220ms;
--motion-emphasis: 400ms;
--motion-reveal: 600ms;
--motion-editorial: 800ms;

--ease-standard: cubic-bezier(0.22, 1, 0.36, 1);
--ease-power2-out: cubic-bezier(0.215, 0.61, 0.355, 1);
--ease-expo-out: cubic-bezier(0.19, 1, 0.22, 1);
```

### 11.2 Motion patterns

- Button press: scale to `0.98` over 100–140ms.
- Button arrow: translate 4–8px over 220–400ms.
- Menu open: opacity plus clip or vertical transform over 300–400ms.
- Sticky navigation condense: transform and width over 400ms.
- Card hover: translate no more than 4px or image scale no more than `1.03`.
- Editorial reveal: opacity plus 16–32px upward movement over 600–800ms.
- Word reveal: optional on one display headline, staggered 35–60ms, once per
  visit.
- Flow transition: 180–260ms crossfade or horizontal movement that preserves
  context.
- Loading: use a stable skeleton or progress label, never an indefinite
  decorative preloader.

### 11.3 Motion restrictions

- No scroll hijacking.
- No parallax inside guided workflows or admin tools.
- No continuous decorative motion behind forms.
- No animation may delay an urgent instruction, error, or primary action.
- Avoid animating layout dimensions when transform or opacity can communicate the
  same change.
- Under `prefers-reduced-motion: reduce`, remove reveals, parallax, autoplay,
  smooth scrolling, and spatial page transitions. Keep only immediate state
  changes.

## 12. Navigation

### 12.1 Desktop

- Use a clear wordmark at the left and 4–6 top-level destinations at the right.
- On immersive heroes, navigation may overlay media when contrast is guaranteed.
- A condensed floating pill may appear after scroll, but it must preserve the
  same landmarks and keyboard order.
- Keep language, appearance, and account controls visually separate from primary
  navigation.

### 12.2 Mobile

- Use a compact Uzbekistan OS mark at the left.
- Use a labelled `Menu` control rather than an unlabeled hamburger.
- Open a full-height opaque sheet with large 44px-minimum navigation rows.
- Keep language and appearance controls visible in the sheet.
- Lock background scroll and return focus to the trigger on close.

## 13. Buttons and links

### 13.1 Primary action

- Filled Uzbekistan OS blue.
- Pill or 14px control radius.
- Minimum height 48px; never below 44px.
- Short verb-led label.
- Optional arrow icon at the trailing edge.

### 13.2 Secondary action

- Blue-soft or neutral surface.
- Border may be omitted when tonal contrast is sufficient.
- Must remain distinguishable from disabled controls.

### 13.3 Editorial link

- Text and directional arrow inside a compact rounded control.
- Arrow may slide on hover or focus.
- Underline or another non-color affordance remains available for inline links.

### 13.4 Destructive action

- Use semantic red only for a genuinely destructive or irreversible operation.
- Require clear text and confirmation proportional to impact.

## 14. Core Uzbekistan OS components

### 14.1 Workflow entry tile

- Large, direct title.
- One-sentence outcome statement.
- Estimated time or number of steps when known.
- Domain and official-source status.
- Optional documentary image on editorial discovery pages.

### 14.2 Progress header

- Shows workflow name, current step, and total steps.
- Remains visible without consuming excessive mobile height.
- Uses text plus a progress indicator.
- Allows safe exit and return when persistence is supported.

### 14.3 Question card

- One primary question.
- Plain-language explanation.
- Large native controls.
- Clear error and why-the-question-is-asked disclosure.
- Primary action aligned consistently.

### 14.4 Grounded answer

- Begins with the direct answer or safe insufficiency.
- Separates requirements, steps, deadlines, fees, and exceptions.
- Attaches citations at claim or paragraph level.
- Displays source title, organization, retrieval date, and applicability.
- Ends with a clear next recommended flow.

### 14.5 Evidence card

- Official organization and title.
- Exact locator or section.
- Short supporting quote when useful.
- Freshness and language metadata.
- External-link affordance.
- Warning state for conflicts or approaching expiry.

### 14.6 Checklist

- Clear completed, current, blocked, and optional states.
- Text labels accompany state icons.
- Group by moment: before travel, arrival, first week, renewal, departure.
- Support print and accessible export later without changing visual semantics.

### 14.7 Admin and reviewer surfaces

- Use compact utility typography and stable columns.
- Preserve visible source and lineage context.
- Keep filters and bulk context separate from record actions.
- Use split views for queue plus artifact detail when space permits.
- Do not apply floating image collages, huge type, or scroll reveals.

## 15. Page archetypes

### 15.1 Home

1. Cinematic or high-quality static hero.
2. Short oversized promise focused on navigation and certainty.
3. Immediate conversational entry field.
4. Offset domain/workflow discovery instead of a uniform card wall.
5. Trust chapter explaining official evidence and citations.
6. High-priority workflow rail.
7. Calm, information-rich footer.

### 15.2 Domain landing

1. Editorial domain headline.
2. One human image or quiet video.
3. Most common decisions and tasks.
4. Workflow list organized by user goal.
5. Official-source coverage and update status.

### 15.3 Guided workflow

1. Stable progress header.
2. One question per view.
3. Contextual explanation.
4. Accessible answer controls.
5. Back and continue actions.
6. Summary and evidence-backed outcome.

### 15.4 Knowledge article

1. Title, applicability, review date, and language.
2. Direct summary.
3. Requirements and ordered steps.
4. Fees, dates, exceptions, and responsible authority.
5. Claim-level official citations.
6. Related workflows.

### 15.5 Admin dashboard

1. Operational summary.
2. Source eligibility and crawl controls.
3. Recent ingestion jobs and errors.
4. Review queue.
5. Artifact detail and comparison.
6. Publication, expiration, and re-index controls.

## 16. Responsive behavior

Suggested breakpoints:

```css
--breakpoint-sm: 30rem; /* 480px */
--breakpoint-md: 48rem; /* 768px */
--breakpoint-lg: 64rem; /* 1024px */
--breakpoint-xl: 80rem; /* 1280px */
```

- Design mobile first at 320px without horizontal scrolling.
- At 390px, editorial display text may reach roughly 50px but must not clip.
- At 768px, move from one column to meaningful two-column compositions.
- At 1024px, enable the full 12-column editorial grid.
- At 1280px and above, increase negative space before increasing body measure.
- On mobile, reorder visual collages into a logical reading sequence or omit
  nonessential images.
- Sticky controls must not cover validation errors or the final lines of content.

## 17. Localization

- Do not hard-code line breaks in translated headings.
- Allow controls to grow by at least 40% horizontally.
- Avoid fixed-height text containers.
- Test long Russian headings and Uzbek apostrophe forms.
- Dates, numbers, currencies, and names use locale-aware formatting.
- Do not use flags as language selectors.
- Preserve source-language information when a citation differs from the response
  language.
- Keep legal meaning and evidence lineage more important than matching line count.

## 18. Accessibility

- Use semantic landmarks and one meaningful `h1` per page.
- Preserve sequential heading structure even when display sizes vary.
- All interactive targets are at least 44 by 44 CSS pixels.
- Visible focus uses a 3px semantic focus ring with 3px offset.
- Text contrast meets at least 4.5:1; large text meets at least 3:1.
- Controls and meaningful graphics meet at least 3:1 against adjacent colors.
- Color never carries status alone.
- Provide alt text for informative imagery and empty alt text for decorative
  imagery.
- Supply captions or transcripts for informative video.
- Carousels have labelled controls, pause behavior, and no forced autoplay.
- Content reflows at 400% zoom.
- Reduced motion is part of every component's acceptance criteria.

## 19. Content voice

Use calm, direct, non-judgmental language.

Prefer:

- `You may need to register within three working days.`
- `We could not verify this from a current official source.`
- `Bring these documents.`
- `This applies to citizens of…`

Avoid:

- institutional filler;
- promises of approval;
- unexplained acronyms;
- dramatic marketing language inside a task;
- `easy`, `simple`, or `just` when a process may be difficult;
- legal conclusions that exceed cited evidence.

## 20. Design tokens and implementation

`packages/design-system/tokens.css` remains the runtime token source of truth.
This document defines the intended system and future token direction. When
implementing this specification:

1. Change semantic tokens before adding page-specific literals.
2. Preserve existing token names when their meaning remains correct.
3. Add fluid editorial type and section-spacing tokens centrally.
4. Use semantic colors rather than raw palette values in components.
5. Keep light and dark values in the same semantic API.
6. Update the live `/design-system` catalogue with each component change.
7. Add visual regression coverage for light, dark, mobile, desktop, English,
   Uzbek, and Russian.

Do not paste reference-site CSS into the project.

## 21. Do and do not

### Do

- Use one oversized message to orient a discovery page.
- Pair cinematic imagery with a concrete user goal.
- Use asymmetric layout to establish hierarchy.
- Keep workflow controls stable and predictable.
- Make official evidence easy to inspect.
- Use black and white confidently, with blue for action.
- Let strong photography carry visual interest instead of decorative gradients.
- Use motion once, with purpose.

### Do not

- Copy the reference site's page composition literally.
- Use its logos, images, copy, or proprietary font.
- Turn every screen into a marketing page.
- Place display type inside forms or data tables.
- Scatter tiny images around procedural content.
- Hide required information behind motion.
- Use decorative video in high-risk tasks.
- Create light-only components.
- Sacrifice localization or accessibility for a precise line break.

## 22. Review checklist

Every new or redesigned screen must answer yes to the following:

### Hierarchy

- Is the primary purpose clear within five seconds?
- Is there one obvious next action?
- Does the display treatment match editorial or utility mode?

### Trust

- Are claims, evidence, freshness, and applicability clear?
- Are uncertainty and blocked states explicit?
- Does the design avoid implying government endorsement?

### Layout

- Does it follow the responsive grid and reading measures?
- Is negative space creating hierarchy rather than hiding content?
- Does the screen work from 320px through wide desktop?

### Type and localization

- Are English, Uzbek, and Russian tested?
- Are headings allowed to wrap naturally?
- Is procedural text comfortably readable?

### Media

- Is the asset licensed, relevant, and privacy-safe?
- Does it have correct alt text, focal point, and fallback?
- Can the page work without video or animation?

### Interaction

- Are keyboard, focus, hover, active, disabled, loading, success, warning, and
  error states designed?
- Are controls at least 44px?
- Does reduced-motion mode remain complete and understandable?

### Appearance

- Does the screen pass in both light and dark mode?
- Does it remain usable with increased contrast?
- Are semantic colors and tokens used consistently?

## 23. Reference interpretation summary

The reference site's strongest lesson is not a specific font, layout, or
animation. It is the discipline to make one idea dominant at a time. Uzbekistan
OS should apply that discipline to civic guidance: one decision, one clear next
step, one visible evidence trail, and no ambiguity about what is known.

## 24. Approved visa landing-page specification

The public landing page is now the visa-first entry point for Uzbekistan OS. Its
visual source of truth remains Figma node `2409:213` in the linked Lumos
community file, together with the approved Uzbekistan OS reference image
`uzb os main.png`. The frame's visual hierarchy, spacing, typography, color,
imagery, radii, and component language remain authoritative, while its product
copy and information architecture are adapted to help foreign visitors select
and understand the correct Uzbekistan visa route.

### 24.1 Desktop composition

- Use a 1280px maximum canvas with a 1232px main content width.
- Header: 88px high, 48px horizontal padding, wordmark left, black
  `Sign up` pill right. The action opens the Uzbekistan OS account-creation
  entry point.
- Hero image: 1232px by 600px, 32px top radii, the approved
  `hero-background.avif` asset, and a lower fade into the `#fcfcfc` page
  background.
- Hero statement: centered `UZBEKISTAN VISA GUIDE` label, two-line 72px
  `Find the right visa for Uzbekistan` headline, 20px supporting copy, paired
  black/outlined pill actions, and a short nationality-dependent rules notice.
  The primary action is `Create free account`; browsing the public visa content
  remains a secondary action.
- Trust features: four equal columns explain the visa decision sequence:
  passport, purpose, document file, and post-arrival compliance. Preserve the
  48px gaps, 64px pastel icon circles, dividers, and centered copy.
- Route cards: retain the four equal 400px-high Figma cards and exact exported
  textures, icons, blue/green/purple/orange gradients. Their labels become
  `Visa-free entry`, `Electronic visa`, `Business & work`, and
  `Study & family`.
- Before public route discovery, show a dark personal-workspace chapter that
  explains the signed-in value: exact visa route, complete document checklist,
  application sequence, processing time, fees and validity, and arrival
  requirements. Repeat the account-creation action in this chapter.
- The route cards are followed by three progressive entry-path panels:
  visa-free, e-visa, and consular visa. Each explains applicability, the key
  evidence, and links only to an official government source.
- Common visa guides use keyboard-accessible native disclosure controls. The
  complete catalogue follows and includes every Ministry of Foreign Affairs
  non-electronic category, grouped by purpose without changing the official
  code or meaning.
- The final chapters cover passport readiness, invitation support, address
  registration, overstay escalation, and official next steps. Entry permission
  and residence registration must never be presented as the same obligation.
- Footer assurance bar: 1232px wide, 24px radius, subtle border, official-source
  assurance and content-review date left, and an outlined `Back to top` pill
  right.

Visa content maps to the approved Immigration MVP domain. References to work,
study, business, treatment, or family are visa purposes, not an expansion of the
backend domain model. The page does not collect passport data, determine legal
eligibility, issue a visa, or imply that a category guarantees entry.

### 24.2 Content and evidence rules

- Use current official Ministry of Foreign Affairs, e-Visa, and my.gov.uz pages
  as the public authority for visa and registration claims.
- Treat nationality lists, consular fees, processing periods, investment
  thresholds, and administrative penalties as changeable. Point users to the
  official page and use a `confirm before applying` notice.
- When supplied research briefs conflict with the official category catalogue,
  use the official catalogue. In particular, the catalogue identifies `A-1` as
  the student category and `A-2` as the teacher category.
- Do not present a business visa as work authorization or a family/visitor visa
  as permanent residence.
- Do not claim that e-visa availability applies to every nationality. The
  official portal determines whether the user is visa-free, e-visa eligible, or
  needs a consular route.
- Keep urgent overstay guidance action-oriented without calculating a fine from
  stale base-calculation amounts.
- Account creation must never be simulated. Until the configured identity
  provider and `/auth/register` implementation are live, the signup screen must
  explicitly state that no personal details are collected and keep submission
  disabled.

### 24.3 Responsive adaptation

The desktop composition is visually authoritative. Below 1024px, features and
categories reflow to two columns. Below 768px, category cards become a single
column, the hero type scales fluidly, fixed line breaks relax, and actions wrap
without horizontal scrolling. All controls retain a minimum 44px target,
visible focus, semantic labels, and reduced-motion behavior.

### 24.4 Asset rules

Landing-page glyphs are the exact exports from the approved Figma frame and
live under `apps/web/public/landing`. The hero uses the separately approved
`hero-background.avif` asset supplied on 2026-08-09. Do not redraw, hotlink, or
recolor these assets. Decorative imagery and glyphs use empty alternative text.
