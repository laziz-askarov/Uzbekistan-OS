# ADR 0008: Fail-closed authenticated administration API

- Status: Accepted for the administration HTTP slice
- Date: 2026-08-01

## Context

The reviewer-control and publication services previously had no HTTP boundary. Exposing them requires verified external credentials, internal principal resolution, role enforcement, consistent errors, request tracing, and one transaction spanning identity activity, domain changes, and immutable audit records. The launch authentication provider and user-facing sign-in experience remain open under D-003.

## Decision

- Accept Bearer credentials only through an injected `IdentityVerifier` interface. A verifier returns a provider and subject only after completing its provider-specific cryptographic and policy checks.
- Configure a disabled verifier by default. Authenticated routes return `authentication_unconfigured` and HTTP 503 until an approved adapter is installed; no development backdoor token is provided.
- Resolve verified provider/subject pairs to provisioned, active internal principals and application-owned roles. Never accept principal IDs or roles from headers, query parameters, or request bodies.
- Propagate the application request ID into the authenticated principal, review audit events, and publication audit events.
- Expose `/auth/me`, reviewer claim/decision, extraction comparison, and publication endpoints under `/api/v1`.
- Keep reviewer and publisher authorization in the domain services as a second enforcement boundary beneath HTTP authentication.
- Commit the request-scoped SQLAlchemy session only after a successful request and roll it back on any exception. Repository methods continue to flush without committing.
- Return authentication, domain, and request-validation failures through the standard error envelope. Validation details contain only location, message, and type; invalid request values are not echoed.
- Describe the implemented endpoints in the checked-in OpenAPI contract and verify operation IDs, paths, and Bearer security against FastAPI's runtime schema.

## Consequences

- The administration routes are safe to deploy before an authentication provider is selected because they fail closed.
- A public login or token issuer is not implemented. Enabling the routes requires a separately reviewed verifier adapter plus principal and role provisioning.
- Exact transaction atomicity now occurs at the request boundary, covering authentication activity, review/publication writes, and audit events.
- Reviewer queue listing, pagination, reassignment, UI, and token issuance/revocation remain future slices.
