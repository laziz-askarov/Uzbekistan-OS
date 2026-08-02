# Conversation context runbook

## Safety boundary

Conversation context is personalization input, never official evidence. The
grounded-answer prompt and API-layer claim validator both preserve this
distinction. If current eligible retrieval is insufficient, a remembered answer
or summary cannot be used to answer the question.

The assembler:

- keeps at most eight recent user/assistant turns;
- applies a 16,000-character context ceiling;
- excludes deleted, duplicate, orphaned, or control-pattern messages;
- accepts only exact-quote-cited summaries of older messages;
- prevents summary/recent-window overlap;
- fingerprints accepted state without requiring raw-content logs; and
- serializes `context_is_untrusted: true` and
  `use_as_official_evidence: false`.

## Summary contract

Each summary statement requires a stable statement ID, concise text, and one or
more citations containing a prior message ID plus an exact quote. The summary
records the highest source-message ordinal it covers. A language mismatch,
unknown/deleted source, quote mismatch, recent-window overlap, unsupported
statement, or size overrun rejects the whole summary.

Do not persist raw provider summaries before the same validator passes. Do not
log message or summary content in telemetry. Record only request ID, context
fingerprint, counts, character totals, quarantine codes, latency, and validation
outcome.

## Remaining persistence decisions

D-008 must define retention, deletion/export timing, analytics consent, and
whether guest history may be transferred to an account. D-003 must define the
verified principal/session boundary. Until then, this internal context core does
not create conversation database tables or public conversation routes.

## Validation

```bash
apps/api/.venv/bin/python -m ruff check apps/api
apps/api/.venv/bin/python -m pytest apps/api/tests/test_conversation_context.py apps/api/tests/test_ai_orchestration.py
```
