# AI orchestration operations runbook

## Current boundary

The Phase 4 orchestration core is internal and has no public chat endpoint. The
checked-in prompt registry defines behavior, but no production provider route is
approved or configured. This is intentional: model execution stays unavailable
until D-006 and the evaluation gates are complete.

The request path is:

1. Accept an eligible evidence pack from deterministic retrieval.
2. Return a localized insufficiency response immediately if it has no safe evidence.
3. Resolve the active prompt fingerprint and an approved provider-neutral route.
4. Invoke the configured adapter with response storage disabled and bounded budgets.
5. Parse `grounded-answer.v1` and validate every claim citation against evidence.
6. Return the answer only if every validation check passes; otherwise abstain.

## Fail-closed behavior

- Missing, proposed, disabled, or ambiguous configuration stops model execution.
- Estimated input or requested output beyond route budgets stops before provider use.
- Retryable provider errors receive no more than the route's configured attempts.
- Reported token or cost overruns reject the response.
- Invalid JSON shape, unknown evidence IDs, non-exact quotes, unsupported claims,
  and language mismatch reject the whole answer.
- Provider details and raw errors are not placed in the user-facing answer.

## Prompt change procedure

1. Add a new semantic version; never edit the contents of a released version.
2. Keep no more than one active version for a prompt key.
3. Run unit and frozen evaluation suites and record the prompt fingerprint.
4. Obtain review for safety, multilingual behavior, latency, and cost changes.
5. Activate the version through a normal reviewed deployment.

## Validation

From the repository root:

```bash
apps/api/.venv/bin/python -m ruff check apps/api
apps/api/.venv/bin/python -m pytest apps/api/tests/test_ai_prompts.py apps/api/tests/test_model_gateway.py apps/api/tests/test_grounded_answers.py apps/api/tests/test_ai_orchestration.py
```

Do not enable a provider solely because these unit tests pass. Production requires
approved routes, secret management, structured telemetry without evidence or PII,
and frozen groundedness, citation, safety, multilingual, latency, and cost gates.
