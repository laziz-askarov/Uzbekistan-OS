# ADR 0013: Database row-access boundary

- Status: Accepted
- Date: 2026-08-01

## Context

Phase 2 requires an explicit row-level access decision. The current service has
one API-owned PostgreSQL connection boundary, provider-neutral principals and
roles, public read models for published knowledge, and privileged ingestion and
review models. User-owned profile, conversation, workflow-progress, and
feedback tables are still planned.

PostgreSQL row-level security can add defense in depth, but enabling it before
the user-owned tables and production database roles exist would create policy
stubs that are not exercised by the running application.

## Decision

- The API remains the mandatory authorization and ownership boundary for the
  MVP service. Browsers, workers, and external identity providers never receive
  direct database credentials.
- Application queries for future user-owned rows must include the verified
  principal or guest-session identifier in the repository method signature and
  predicate. Repository tests must prove cross-principal access fails.
- Published knowledge is read through eligibility views or repositories that
  exclude unpublished, expired, superseded, future-effective, and inapplicable
  versions.
- Ingestion, review, publication, identity-role, and audit tables are never
  exposed through public database roles. Their API operations remain
  role-gated and fail closed.
- PostgreSQL RLS is deferred until the migrations for user-owned tables and
  separate production runtime/migration roles are introduced. That migration
  must enable and force RLS, define ownership policies, and include connection-
  role integration tests before any direct multi-tenant access pattern ships.
- Production database roles follow least privilege: a migration owner applies
  DDL, the API runtime receives only required DML/execute privileges, and
  backup/observability roles are separate read-only identities.

## Consequences

- The current schema does not claim untested RLS protection.
- Authorization remains deterministic and testable in the API layer, matching
  the repository architecture guidance.
- User-owned table migrations cannot be considered complete without either the
  deferred RLS implementation or an explicit security review that preserves
  the API-only boundary.
