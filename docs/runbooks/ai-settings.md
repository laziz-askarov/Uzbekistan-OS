# MVP AI settings runbook

## Baseline

| Setting | MVP value | Purpose |
| --- | ---: | --- |
| `AI_GENERATION_ENABLED` | `false` by default | Explicit deployment switch; D-006 and the checked-in route are approved |
| `OPENAI_GENERATION_MODEL` | `gpt-5.4-mini` | Approved balanced quality/cost provider model |
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
| Web fallback | `false` by default | Explicit opt-in; searches and fetches only approved official Uzbekistan domains when local evidence is empty |
| Web fallback source/fetch limits | 4 sources / 750 KB each | Bound latency, cost, and untrusted input size |

The supported languages are English, Uzbek, and Russian. The configured domains
are Immigration, Tourism, Business Registration, Healthcare, and Everyday
Living. These are validated product invariants.

## Deployment procedure

Before setting `AI_GENERATION_ENABLED=true`:

1. Supply `OPENAI_API_KEY` through the deployment secret manager, never Git.
2. Configure `SUPABASE_URL` and the Supabase publishable key so the API can
   verify customer access tokens.
3. Set the environment-specific source registry path and publish reviewed,
   unexpired Uzbek knowledge candidates.
4. Run the frozen high-risk, adversarial, abstention, latency, and cost gates.
5. Run staging smoke/load tests and verify that provider response storage remains
   false.
6. If live official-domain fallback is approved, set `AI_WEB_FALLBACK_ENABLED=true`.
   It reuses `OPENAI_API_KEY`; do not add a browser or search credential to the web app.
7. Set `AI_GENERATION_ENABLED=true` for a small controlled traffic slice with
   rollback to disabled generation.

Changing only the environment flag cannot bypass the checked-in approval state,
credential checks, retrieval eligibility, structured-output validation, or exact
evidence-quote validation.

The web fallback never searches arbitrary domains. It obtains its domain allowlist
from active, official Uzbekistan sources already approved in the database, rejects
redirects and non-HTTPS URLs, blocks private/reserved network addresses, bounds every
response, strips executable HTML, and sends the resulting evidence through the same
quote and citation validator as local knowledge.

## Validation

From the repository root:

```bash
apps/api/.venv/bin/python -m ruff check apps/api
apps/api/.venv/bin/python -m pytest apps/api/tests/test_ai_settings.py apps/api/tests/test_model_gateway.py
```
