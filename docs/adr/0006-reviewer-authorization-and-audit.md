# ADR 0006: Reviewer authorization and immutable audit

- Status: Accepted for the reviewer-control slice
- Date: 2026-07-31

## Context

Extraction artifacts are untrusted intermediate data. Human decisions need deterministic authorization, concurrency control, traceability, and evidence comparison without allowing an extraction approval to bypass knowledge validation or publication rules.

## Decision

- Require an application-owned reviewer context containing a verified actor ID and either the `content_reviewer` or `admin` role. Only trusted authentication middleware may construct this context.
- Allow `pending → in_review → approved|rejected`. Claiming an already assigned item is idempotent only for the same reviewer.
- Require the assigned reviewer to make the terminal decision, including when another actor has the admin role.
- Require a non-empty decision reason, but store only its SHA-256 in the immutable audit payload to reduce retention of free-form sensitive text.
- Lock review rows during state transitions and persist the review update and audit insert in one caller-owned database transaction.
- Enforce assignment and decision-field consistency with PostgreSQL check constraints.
- Reject updates and deletes of audit events with a database trigger.
- Verify extraction bytes against their database checksum before comparison and report section additions, removals, modifications, and unchanged sections.
- Treat extraction approval as an editorial gate only. It does not create or publish a knowledge version.

## Consequences

- No reviewer HTTP routes are exposed until authentication and role mapping are implemented.
- Concurrent reviewers cannot legitimately claim or decide the same item when repository calls run in a transaction.
- Audit correction requires a compensating event rather than mutation.
- Transactional publication still requires a separate, schema-valid candidate with citations, language, domain, effective dates, and version metadata.
