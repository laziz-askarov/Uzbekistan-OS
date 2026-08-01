# Responsive flow wireframes and acceptance criteria

Date: 2026-08-01

## Purpose

These low-fidelity wireframes define the reusable application surfaces and
responsive behavior for every MVP workflow. They are implementation contracts,
not visual-polish specifications. The 15 launch workflows approved under D-001
are recorded in `launch-workflows.md`; each inherits these criteria and must add
domain-specific content, eligibility, source, and completion checks before launch.

## Breakpoints

| Viewport | Layout contract |
| --- | --- |
| Mobile, below 48rem | One content column, bottom or compact top navigation, filters in a labelled disclosure/drawer, primary action visible without horizontal scrolling |
| Tablet, 48rem–63.99rem | One or two columns according to content density, persistent navigation where space permits, readable line length capped near 70 characters |
| Desktop, 64rem and above | Persistent navigation, main content plus optional contextual rail, content order identical to the mobile reading order |

At every size, content must reflow at 400% zoom without two-dimensional scrolling,
except for genuinely two-dimensional data. Pointer targets are at least 44 by 44
CSS pixels, focus order follows reading order, and status never relies on color
alone.

## Global application shell

```text
MOBILE                         TABLET / DESKTOP
┌──────────────────────┐       ┌─────────┬──────────────────────┬──────────┐
│ Brand   Language Menu│       │ Brand   │ Page title / actions │ Profile  │
├──────────────────────┤       ├─────────┼──────────────────────┼──────────┤
│                      │       │ Primary │                      │ Optional │
│ Main page content    │       │ nav     │ Main page content    │ context  │
│                      │       │         │                      │ rail     │
├──────────────────────┤       └─────────┴──────────────────────┴──────────┘
│ Home Search Work Me  │
└──────────────────────┘
```

Acceptance criteria:

- A skip link moves focus to the page's main landmark.
- The current page is identified in navigation with text or `aria-current`.
- The language selector keeps the current task and entered data when feasible.
- Guest and signed-in states have explicit names; authentication is never implied
  only by an avatar.
- Global errors appear near the page title and move focus only after a failed
  user-initiated submission.

## Guidance discovery and search

```text
MOBILE                         TABLET / DESKTOP
┌──────────────────────┐       ┌────────────┬─────────────────────────────┐
│ What do you need?    │       │ Filters    │ Search + result count       │
│ [Search____________] │       │ Domain     ├─────────────────────────────┤
│ [Filters (2)]        │       │ Language   │ Result title      Verified  │
├──────────────────────┤       │ Audience   │ Summary + source date       │
│ 12 results           │       │            ├─────────────────────────────┤
│ Result title         │       │            │ Result title      Updated   │
│ Summary + source date│       └────────────┴─────────────────────────────┘
└──────────────────────┘
```

Acceptance criteria:

- Search has a persistent accessible label, submit control, and result count
  announcement.
- Filters are keyboard operable, individually removable, and reflected in the URL.
- Loading, no-result, partial-data, error, and offline states provide a next action.
- Result cards expose title, topic, freshness, and verification status as text.
- Cursor pagination preserves filters, scroll context, and focus.

## Knowledge and source detail

```text
MOBILE                         DESKTOP
┌──────────────────────┐       ┌──────────────────────┬───────────────┐
│ Back to results      │       │ Title + status       │ On this page  │
│ Title + status       │       │ Summary              │ Requirements  │
│ Summary              │       │ Requirements         │ Steps         │
│ Requirements         │       │ Ordered steps        │ Sources       │
│ Ordered steps        │       │ Fees / applicability │               │
│ Sources + dates      │       │ Sources + dates      │               │
└──────────────────────┘       └──────────────────────┴───────────────┘
```

Acceptance criteria:

- Applicability, requirements, fees, and ordered steps use semantic headings and
  lists.
- Every factual section exposes its source, publisher, publication or retrieval
  date, language, and verification status.
- Superseded or expired guidance is prominent before the affected content.
- External source links identify destination and open in the same tab by default.
- A user can report inaccurate or inaccessible content from the relevant section.

## Assistant conversation

```text
MOBILE                         DESKTOP
┌──────────────────────┐       ┌──────────┬────────────────────┬───────────┐
│ Conversation title   │       │ History  │ Conversation       │ Sources   │
├──────────────────────┤       │          │ User message       │ cited in  │
│ User message         │       │          │ Answer + citations │ answer    │
│ Answer + citations   │       │          │ Workflow prompt    │           │
│ Workflow prompt      │       │          ├────────────────────┤           │
├──────────────────────┤       │          │ [Message_________] │           │
│ [Message___________] │       └──────────┴────────────────────┴───────────┘
│ [Send]               │
└──────────────────────┘
```

Acceptance criteria:

- Streaming output is announced in coherent chunks; focus remains in the composer.
- Stop, retry, copy, and feedback controls have explicit accessible names.
- Citations are linked from the exact claim and available in reading order.
- The interface distinguishes sourced guidance, clarification questions, workflow
  progress, and system errors.
- A connection failure retains the draft and provides a non-destructive retry.

## Workflow list, detail, and progress

```text
MOBILE                         DESKTOP
┌──────────────────────┐       ┌────────────┬─────────────────────────────┐
│ My workflows         │       │ Workflows  │ Workflow title + status     │
│ In progress (2)      │       │ list       │ Eligibility / requirements  │
│ [Workflow card]      │       │            │ Step 2 of 5                 │
│ [Workflow card]      │       │            │ Current step and evidence   │
├──────────────────────┤       │            │ [Save] [Mark complete]      │
│ Selected workflow    │       └────────────┴─────────────────────────────┘
│ Step 2 of 5          │
│ Current step         │
│ [Continue]           │
└──────────────────────┘
```

Acceptance criteria:

- Progress is expressed as text and programmatic state, not color alone.
- Users can save, resume, revisit completed steps, and see what will be retained.
- Preconditions and blocking requirements appear before an action begins.
- Destructive restart or abandonment requires confirmation and explains impact.
- Source changes that affect saved progress trigger a visible revalidation state.

## Identity, profile, and guest continuity

Acceptance criteria:

- Registration, sign-in, refresh failure, sign-out, and guest continuation have
  distinct states and recovery paths.
- Fields use visible labels, connected instructions, appropriate autocomplete, and
  inline errors summarized after submission.
- Guest-to-account conversion explains exactly which conversations and workflow
  progress will transfer before consent.
- Profile language, region, and accessibility preferences are editable without
  requiring unrelated personal data.
- Session expiry retains safe unsent input and returns the user to the same task.

## Reviewer and ingestion administration

Acceptance criteria:

- Queues support keyboard navigation without requiring table-specific shortcuts.
- Priority, review state, freshness, source environment, and retry status are text.
- Evidence, extraction, comparison, approval, publication, and audit context stay
  connected through stable identifiers.
- Approve, reject, retry, publish, expire, and re-index actions state prerequisites,
  show progress, and confirm the resulting state.
- Unauthorized or stale actions fail closed and never optimistically present a
  successful final state.

## Launch-flow approval template

Use this table for every workflow selected under D-001. Portfolio approval is
complete; a workflow is not implementation-ready until every cell has an
accountable reviewer and evidence link.

| Acceptance dimension | Required evidence |
| --- | --- |
| User and outcome | Named primary audience, problem, completion outcome, and owner |
| Eligibility and exceptions | Reviewed applicability rules, exclusion cases, and escalation path |
| Authoritative sources | Approved source URLs, precedence, language, freshness SLA, and crawl permission |
| Mobile / tablet / desktop | Reviewed screenshots or prototypes at all three layout contracts |
| Accessibility | Keyboard, screen-reader, 400% zoom/reflow, contrast, target size, reduced-motion, and error-state results |
| Data and privacy | Data collected, retention, guest/account transfer, authorization, and deletion behavior |
| Failure and recovery | Loading, empty, partial, stale, offline, timeout, authorization, and retry states |
| Analytics and support | Consent-aware success/failure measures and support escalation path |

## Review status

The shared responsive surface contract and D-001 portfolio selection are approved
for Phase 2. Flow-specific source mappings, localized content, screenshots, and
implementation evidence remain later launch-readiness work, not Phase 2 blockers.
