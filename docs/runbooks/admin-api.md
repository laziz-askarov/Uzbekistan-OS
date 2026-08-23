# Administration API runbook

## Implemented endpoints

All paths are relative to `/api/v1` and require `Authorization: Bearer <token>`.

- `GET /auth/me` resolves the verified subject to its internal principal and roles.
- `GET /admin/sources` merges the configured registry with source and latest-job state.
- `POST /admin/sources` creates an audited, idempotent, manual-only official source with a required `Idempotency-Key`.
- `POST /admin/sources/{source_id}/uploads` ingests bounded official evidence with a required `Idempotency-Key`.
- `GET /admin/ingestion/jobs` returns recent crawler and upload jobs.
- `POST /admin/ingestion/jobs` queues an approved automatic source with a required `Idempotency-Key`.
- `GET /admin/reviews` returns a status-filtered, prioritized queue with source context.
- `POST /admin/reviews/{review_item_id}/claim` claims a pending review item.
- `POST /admin/reviews/{review_item_id}/decision` approves or rejects the assigned item.
- `GET /admin/artifacts/{artifact_id}` returns checksum-verified extraction content.
- `GET /admin/artifacts/{artifact_id}/comparison` returns a checksum-verified section comparison.
- `POST /admin/publications` publishes an approved, evidence-bound knowledge candidate.
- `POST /admin/documents/{document_id}/expire` expires the current published version.
- `POST /admin/documents/{document_id}/reindex` queues an eligible version with a required `Idempotency-Key`.

Every response carries `x-request-id` and the standard response metadata. Supply `x-request-id` from a trusted upstream when available; otherwise the API generates one.

## Admin consoles

The responsive ingestion dashboard is served at `/admin`. It supports source eligibility inspection, audited manual-source creation, bounded PDF/HTML/XHTML/text upload, existing or newly named topic assignment, approved crawler enqueue, job status/error monitoring, search, and dark mode. Admin-created sources require an HTTPS URL on the declared official organization's domain, are fixed to `manual_only`, and cannot expand crawler scope or schedules. Uploads are limited to 10 MB; readable PDFs are normalized to private page-preserving Markdown, and every upload feeds the same checksum, immutable evidence, extraction, and human-review pipeline as crawls.

Read-only source, topic, and job queries require PostgreSQL and the environment-bound registry only. They remain available when Redis or evidence storage is degraded so administrators can inspect state and errors. Manual document upload is processed synchronously and requires PostgreSQL plus evidence storage, while crawler enqueue continues to fail closed until Redis is configured.

Apply migration `20260823_0008` before enabling source creation. Admin-created source metadata lives in `ingestion.managed_source_configs`; the source and official organization remain in the canonical `knowledge` tables. Creation uses request hashing for deterministic idempotency replay and writes `ingestion.source_created` to the immutable audit stream in the same transaction. Registry synchronization excludes managed source and organization rows from deactivation.

The reviewer console is served at `/admin/reviews`. It supports queue filtering, source and lineage inspection, section comparison, claiming, reasoned approval or rejection, evidence-bound publication, expiration, and re-index queueing. Publisher controls appear only for a principal with `knowledge_publisher` or `admin`. Both consoles reuse the signed-in Supabase session and keep its short-lived Bearer token in page memory only; they do not put credentials in URLs or persistent browser storage. The web route verifies the current `public.user_roles` assignment before rendering, and the API independently resolves the token subject through `identity.principals` and `identity.principal_roles`.

The console deliberately displays the authentication failure when the verifier is disabled. Do not add a development bypass to the browser application. Configure and test the approved verifier, provision the principal and roles, then sign in again if the web role claim was added after the current session was issued. The browser uses the same Bearer boundary as other API clients.

## Authentication adapter requirements

The committed default is deliberately disabled and returns HTTP 503 with `authentication_unconfigured`. Before enabling an environment, install a reviewed `IdentityVerifier` adapter that:

1. verifies token signature and algorithm without accepting algorithm downgrades;
2. validates issuer, audience, expiry, not-before, and environment/tenant policy;
3. applies the selected revocation or session-invalidating policy;
4. returns a stable provider and subject pair only after all checks pass;
5. maps verification failures to a generic authentication error without leaking token data; and
6. never logs the Bearer token.

Provision the resulting `(provider, subject)` in `identity.principals` and grant application roles through `identity.principal_roles`. Unknown and disabled principals are denied even when the external token is valid.

## Transaction behavior

The request dependency owns the database transaction. It commits only after the endpoint completes and rolls back on exceptions. Do not add commits to identity, review, publication, or audit repositories; doing so would break atomic rollback.

An exact publication replay returns the existing publication result. Review transition conflicts and changed-candidate publication replays return HTTP 409. Integrity failures must be treated as evidence incidents, not bypassed through direct database updates.

## Validation

From the repository root:

```bash
apps/api/.venv/bin/python -m ruff check apps/api scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests
apps/api/.venv/bin/python scripts/validate_contracts.py
apps/api/.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head --sql
```

Before enabling an authentication adapter, add adapter-specific tests for invalid signatures, issuers, audiences, expiry, clock skew, and revocation. Run request-level concurrency and rollback tests against disposable PostgreSQL.

Validate both admin routes at desktop and narrow-screen breakpoints. For `/admin`, cover keyboard focus, source search, empty/error states, ineligible disabled actions, file type/size failures, upload feedback, crawler enqueue, job errors, and dark mode. For `/admin/reviews`, cover claim ownership, reason-required decisions, publication fields, required expiration reason, and re-index feedback.
