# ADR 0021: Bounded conversation context and cited summaries

**Status:** accepted for the Phase 4 internal core

**Date:** 2026-08-02

## Context

The PRD requires conversational memory, but earlier conversation content is not
official evidence and may contain stale facts, deleted data, prompt injection,
or model errors. D-008 still leaves persistence retention and deletion/export
periods open. Phase 4 needs a safe context boundary that does not pre-empt that
policy or weaken retrieval.

## Decision

- Model conversation context as application-owned structured data containing
  user/assistant turns only. Provider response IDs are never canonical state.
- Retain at most eight recent turns and 16,000 context characters for a model
  request. Prefer newest complete turns when the character budget is exhausted.
- Exclude soft-deleted messages, orphan assistant messages, duplicate message
  identity/ordering, and messages containing reserved orchestration or
  instruction-override patterns.
- Accept a summary only when each statement cites one or more older messages and
  includes an exact quote from each cited message. Require deterministic lexical
  support and reject the entire summary on any invalid statement.
- Do not duplicate messages between the summary and recent-turn window.
- Mark the serialized context as untrusted and explicitly unusable as official
  evidence. Every procedural factual claim must still be supported by a newly
  eligible retrieval evidence pack.
- Version the grounded-answer prompt to 1.1.0 so the model is told that
  conversation text and summaries are data, not instructions or citations.
- Fingerprint the accepted context for reproducibility and telemetry without
  logging its raw contents.

## Consequences

Conversation continuity can inform personalization and query interpretation,
but cannot establish visa eligibility, deadlines, fees, legal requirements, or
medical guidance. Persistence tables, ownership enforcement, soft-deletion
implementation, export, retention duration, and summary generation remain
blocked on D-003/D-008 and later Phase 5 API work. The current slice validates
supplied summaries; it does not authorize a model to persist them.
