# Phase 3 acceptance record

Date assessed: 2026-08-01

## Scope

Phase 3 builds the auditable path from an approved official source snapshot to a
reviewed, published, chunked, indexed, and retrieval-eligible knowledge version.
The phase cannot be accepted using fixtures presented as production evidence.

## Deliverable status

| Phase 3 requirement | Repository evidence | Status |
| --- | --- | --- |
| Source registry and crawl/fetch adapters | Environment-bound v1.1 registry, fail-closed eligibility, generic HTML/text/PDF fetch and extraction, registry synchronization and scheduling; inert production proposal with five official-source candidates | Core complete; source ownership, crawl permission, and three proposed source-specific adapters require approval/implementation |
| Snapshot through review queue | Content-addressed S3-compatible snapshots/artifacts, normalization, PDF bounds, checksum lineage, deduplication, change detection, Redis retries/DLQ, role-gated queue/compare/claim/decision APIs and UI | Complete against non-production evidence |
| Immutable versions and publication lifecycle | Evidence-bound transactional publication, monotonic versions, source lineage, current pointer, effective dates, immutable audit, expiration lifecycle events, role-gated API/UI | Complete; supersession is exercised through newer publication versions |
| Applicability and retrieval eligibility | Canonical schema applicability fields plus `knowledge.retrievable_chunks`, current/published/effective checks at queue and index claim, live expiry exclusion test | Complete for Phase 3 eligibility; query planning remains Phase 4 |
| Semantic chunking and provenance | Heading/section boundary preservation, paragraph/concept packing, deterministic ordinals/hashes, fragment metadata, per-chunk reviewed citations | Complete |
| Embedding/index jobs | Provider interface, persisted caller-key idempotency, attempts, retry/dead-letter/cancel states, vector validation/upsert, token/latency/cost telemetry | Core complete; production provider, dimensions, ANN index, budgets, and evaluation gate await D-006 |
| Reviewer compare/approve/reject/publish/expire/re-index UI/API | Authenticated admin routes and responsive console; Bearer token remains memory-only | Complete in code; environment use awaits the approved verifier from D-003 |
| Admin source/upload/crawler operations | Responsive `/admin` dashboard, registry-derived eligibility, bounded official-document uploads, idempotent crawler enqueue, recent job/error visibility, dark mode | Complete in code; production actions remain disabled until source and verifier approvals |
| Infrastructure-backed integration evidence | Migration `20260801_0006` applied to local PostgreSQL/pgvector; live rollback-safe test proves index replay, expiration exclusion, and post-expiry rejection | Passed locally on 2026-08-01 |
| First 20 production-quality documents | 21-candidate EN/UZ/RU inventory for Arrival & Entry and Visa Eligibility with explicit evidence gaps | Not complete; official-source approval and human content/domain/translation review required |

## Exit gate evidence

- Source snapshot, extraction artifact, review, publication record, document
  version/source link, chunks, index job, embeddings, lifecycle event, and audit
  event all retain stable identifiers/checksums needed to reproduce lineage.
- The only retrieval eligibility view excludes non-current, non-published,
  not-yet-effective, and expired versions.
- The live PostgreSQL test proves an expired item disappears from that view in
  the same transaction and cannot accept a new index job.
- Model output and provider vectors remain untrusted until structural validation.

## Required approvals before Phase 3 can close

1. Assign accountable owners and crawl policies to each selected official source;
   approve freshness/expiry rules under D-005.
2. Approve and configure the token verifier under D-003, including issuer,
   audience, session/revocation, and recovery policy.
3. Approve the embedding route, dimensions, budgets, and evaluation thresholds
   under D-006, then add the production ANN migration.
4. Resolve whether “one low-risk workflow” means a content-level classification
   or requires a database domain seeded as `low`; all current domains are medium
   or high.
5. Produce and independently review at least 20 evidence-bound documents across
   EN/UZ/RU, including the higher-risk legal/domain review and human translation
   review required by D-004.

Until those approvals and content reviews are recorded, Phase 3 is technically
advanced but **not fully complete**.
