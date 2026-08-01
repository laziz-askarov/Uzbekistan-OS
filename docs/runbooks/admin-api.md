# Administration API runbook

## Implemented endpoints

All paths are relative to `/api/v1` and require `Authorization: Bearer <token>`.

- `GET /auth/me` resolves the verified subject to its internal principal and roles.
- `POST /admin/reviews/{review_item_id}/claim` claims a pending review item.
- `POST /admin/reviews/{review_item_id}/decision` approves or rejects the assigned item.
- `GET /admin/artifacts/{artifact_id}/comparison` returns a checksum-verified section comparison.
- `POST /admin/publications` publishes an approved, evidence-bound knowledge candidate.

Every response carries `x-request-id` and the standard response metadata. Supply `x-request-id` from a trusted upstream when available; otherwise the API generates one.

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
