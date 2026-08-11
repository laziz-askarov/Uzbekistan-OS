# ADR 0007: Provider-neutral identity and transactional publication

- Status: Accepted for the identity/publication slice
- Date: 2026-07-31

## Context

Reviewer and publication actions need durable internal identities even though the launch authentication mechanism remains an open product and security decision. Publication must preserve the approved evidence lineage, enforce separation of duties, and atomically create the knowledge version, chunks, source link, current-version pointer, publication record, and audit event.

## Decision

- Represent people as internal principals keyed by a unique verified `(provider, subject)` pair. Authentication middleware is responsible for verification; request headers and bodies are not trusted identity sources.
- Provision application roles independently of the external identity provider. Seed `content_reviewer`, `knowledge_publisher`, and `admin` roles, and deny access to unknown or disabled principals.
- Keep this internal boundary provider-neutral. ADR 0023 later selected Supabase progressive identity for customer accounts without coupling administrative roles to a provider SDK.
- Keep review and publication permissions separate. An approved review does not publish content, and `content_reviewer` alone cannot publish.
- Publish only from an active source with an `allowed` or `manual_only` policy owned by an active, official organization.
- Publish only a schema-valid candidate whose section order, identifiers, headings, and bodies exactly match the reviewed extraction artifact. Citations must reference the reviewed source, and quoted evidence must occur in the approved section.
- Verify both extraction-artifact and source-snapshot checksums before publication.
- Allow one publication record per review item and persist the candidate SHA-256. An exact retry returns the existing result; a different candidate conflicts.
- Require monotonically increasing semantic version numbers for an existing document.
- Persist the document version, source lineage, chunks, current-version pointer, publication record, and immutable audit event in one caller-owned database transaction. Repository methods flush but do not commit.
- Treat a document slug as one canonical-language stream. Translations use a distinct document slug and may link to another document version through `translation_of_id`.
- Add identity foreign keys to existing review/audit actor columns as PostgreSQL `NOT VALID` constraints. They enforce new writes without blocking development databases that contain legacy actor UUIDs; a later operational migration must backfill and validate them.

## Consequences

- No identity or publication HTTP endpoint is exposed until trusted token verification and route authorization exist.
- External identity changes do not rewrite historical audit or publication lineage.
- Publication failures roll back as a unit when the caller owns a transaction. Correcting published guidance requires a new reviewed version rather than editing an existing version or audit event.
- The first publication boundary supports one reviewed source artifact per version. Composite multi-source evidence packages require an explicit later design.
- Live constraint and concurrency behavior still require PostgreSQL-backed integration tests.
