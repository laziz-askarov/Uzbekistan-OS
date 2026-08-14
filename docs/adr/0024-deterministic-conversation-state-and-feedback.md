# ADR 0024: Deterministic conversation state and contextual feedback

**Status:** accepted for the Phase 4 internal core

**Date:** 2026-08-14

## Context

Bounded recent turns and cited summaries preserve safe conversational continuity,
but free-text history does not reliably distinguish confirmed, inferred, missing,
or conflicting user context. Follow-up queries also need deterministic access to
confirmed applicability without treating conversation memory as official evidence.

## Decision

- Represent conversation state as typed, fingerprinted application data with
  message-and-quote lineage for every fact.
- Permit only confirmed facts to populate retrieval applicability. Inferred facts
  may trigger clarification but cannot exclude knowledge.
- Remove conflicting values from active applicability until the user resolves the
  conflict. Explicit corrections retain source-message lineage.
- Reuse the current workflow as an intent hint only when a follow-up query has no
  independently detected intent.
- Add `needs_clarification` as a non-factual answer outcome. Material missing or
  conflicting context produces one deterministic question without a model call.
- Validate model-reported `context_used` against confirmed state and expose bounded
  limitations, next actions, and evidence lineage in application-owned output.
- Keep conversation state, corrections, and UI feedback outside knowledge-document
  JSON. Knowledge documents continue to hold only reviewed applicability,
  requirements, steps, fees, processing times, sections, and official evidence.
- Do not add persistence tables until the existing retention, deletion, export,
  and ownership decisions are approved.

## Consequences

Follow-up questions can inherit confirmed nationality, residency status, location,
audience, and workflow without letting conversational assertions become evidence.
The planned conversation API can stream explicit context feedback and clarification
metadata. Storage remains intentionally unimplemented, and additional applicability
dimensions require deterministic retrieval support before they can filter content.
