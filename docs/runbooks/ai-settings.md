# MVP AI settings runbook

## Baseline

| Setting | MVP value | Purpose |
| --- | ---: | --- |
| `AI_GENERATION_ENABLED` | `false` | Fail closed until D-006 and frozen evaluations approve the route |
| `OPENAI_GENERATION_MODEL` | `gpt-5.6-terra` | Proposed balanced quality/cost provider model |
| Reasoning effort | `low` | Latency-sensitive grounded answer generation |
| Route timeout / attempts | 7 seconds / 1 | Fit within the 8-second completion target |
| Input / output tokens | 12,000 / 2,000 | Bound evidence, context, latency, and cost |
| Route cost ceiling | $0.05 | Proposed per-request safety ceiling; not an approved forecast |
| Retrieval / evidence items | 8 / 6 | Preserve diversity while bounding supplied evidence |
| Evidence characters | 9,000 | Bound model input and reduce prompt-injection surface |
| Recent / summary-trigger turns | 8 / 12 | Preserve useful continuity with bounded context |
| Summary characters | 4,000 | Bound application-owned conversation state |
| Total context characters | 16,000 | Bound recent turns plus an accepted cited summary |
| Stream / first content / completion | 2s / 3s / 8s | PRD and reliability response objectives |
| Citation benchmark coverage | 95% | PRD minimum; runtime factual-claim coverage remains 100% |
| Provider response storage | `false` | Uzbekistan OS remains the conversation system of record |

The supported languages are English, Uzbek, and Russian. The configured domains
are Immigration, Tourism, Business Registration, Healthcare, and Everyday
Living. These are validated product invariants.

## Approval procedure

Before setting `AI_GENERATION_ENABLED=true`:

1. Freeze representative multilingual, high-risk, adversarial, and abstention
   evaluations with approved source expectations.
2. Record groundedness, claim citation coverage, citation validity, latency,
   token use, and cost for the proposed route.
3. Approve D-006 and change the checked-in route from `proposed` to `approved`.
4. Supply `OPENAI_API_KEY` through the deployment secret manager, never Git.
5. Run staging smoke/load tests and verify that provider response storage remains
   false.
6. Enable a small controlled traffic slice with rollback to disabled generation.

Changing only the environment flag cannot bypass the checked-in approval state.
The API refuses to start when generation is enabled against an unapproved route.

## Validation

From the repository root:

```bash
apps/api/.venv/bin/python -m ruff check apps/api
apps/api/.venv/bin/python -m pytest apps/api/tests/test_ai_settings.py apps/api/tests/test_model_gateway.py
```
