# Ingestion operations runbook

## Validate the registry and ingestion code

From the repository root:

```bash
apps/api/.venv/bin/python scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests/test_ingestion.py apps/api/tests/test_object_store.py
apps/api/.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head --sql
```

The committed development registry is not eligible for automatic fetching. A production run must fail closed until an approved registry entry is supplied.

## Job semantics

- `queued`: ready for a worker claim.
- `running`: one worker owns the current attempt.
- `retry_scheduled`: a transient failure may be retried while attempts remain.
- `succeeded`: the stored result is replayed for the same idempotency key.
- `dead_lettered`: attempts are exhausted or the failure is permanent.
- `cancelled`: an operator stopped the job.

The unique `(source_id, idempotency_key)` constraint is the final concurrency guard. Workers must commit the job transition and snapshot metadata in one database transaction. A content-addressed object left behind by a failed transaction is safe to reconcile because writing different bytes to the same key is prohibited.

## Object storage

Raw source responses and canonical extraction artifacts share the S3-compatible evidence bucket. The adapter stores a SHA-256 value in object metadata and verifies it before accepting a repeated write.

- Set `S3_AUTO_CREATE_BUCKET=true` only for local development.
- Pre-provision and encrypt staging/production buckets; leave auto-creation disabled.
- Restrict the worker identity to the evidence bucket and deny public access.
- Treat a `snapshot_collision` as an integrity incident rather than retrying it.

Each changed snapshot produces one schema-versioned extraction artifact and one `pending` review item. Unchanged responses do not create new review work.

## Administrator uploads and manual crawls

The `/admin` dashboard and its API require the `admin` role. Manual uploads are accepted only when the registry source is official, approved, production-eligible, and has `crawl_policy: allowed` or `manual_only`. Automatic crawler runs require the stricter `allowed` policy. An operator cannot use the dashboard to approve a source or change its URL, adapter, policy, or schedule.

- Upload payloads are base64-encoded JSON to keep request parsing deterministic and are capped at 10 MB after decoding.
- Filenames must be plain names without directory components. Supported media types are PDF, HTML, XHTML, and text.
- The response URL remains the exact approved source URL; source/media mismatch, redirects, oversized content, and unsupported PDFs fail closed.
- Upload and crawl mutations require a caller-supplied idempotency key. Known checksums reuse their immutable snapshot and do not create duplicate review work, even if an older version is uploaded again.
- The database transaction rolls back if queue publication or ingestion fails. Do not bypass the API by writing directly to the evidence bucket.

## PDF controls

A PDF source must be registered explicitly with `source_type: pdf`, and the approved URL must return `application/pdf`. A mismatched source type, missing PDF signature, malformed file, encrypted file, or PDF with no extractable text is a terminal failure.

- `INGESTION_MAX_RESPONSE_BYTES` limits raw response size before parsing.
- `INGESTION_MAX_PDF_PAGES` defaults to 250.
- `INGESTION_MAX_NORMALIZED_CHARACTERS` defaults to 2,000,000 across supported source types.
- Non-empty PDF pages become `Page N` extraction sections so reviewers retain physical-page provenance.
- OCR is intentionally disabled. Do not manually publish text from scanned or password-protected files; obtain an approved accessible source or add a separately reviewed adapter.
- Review complex tables, columns, and reading order against the stored source before approval.

## Reviewer controls

The application review service accepts only a trusted context with a verified actor UUID and the `content_reviewer` or `admin` role. Do not build this context from request headers or body fields.

Legal transitions are:

```text
pending -> in_review -> approved
                     -> rejected
```

- The row must be locked and the review update plus audit insert committed together.
- Only the assigned reviewer may approve or reject the item.
- Record a concise decision reason without personal or applicant information.
- Approval confirms extraction quality only; it does not publish knowledge.
- Audit events cannot be updated or deleted. Corrections require a new compensating event.
- Artifact comparison verifies stored bytes against database lineage before producing a section-level diff.

## Failure triage

1. Confirm the registry entry remains approved and that its crawl policy has not changed.
2. Inspect the job's structured `error`, attempt count, and source URL without logging response bodies.
3. Treat timeouts, HTTP 408/425/429, and HTTP 5xx as candidates for bounded retry.
4. Treat redirects, unsupported or mismatched content, oversized responses, malformed/encrypted/image-only PDFs, changed destination URLs, and approval failures as permanent until reviewed.
5. Never move a snapshot into the publication path manually. Requeue through the same idempotent job boundary after correcting the cause.

## Registry synchronization and scheduling

Registry version 1.1 is synchronized into PostgreSQL before the worker and scheduler start. Synchronization fails if the registry environment does not match `APP_ENV`, if an organization country is not seeded, or if stable IDs conflict with an existing slug or URL. Entries absent from the configured environment registry are marked inactive, never deleted.

Only approved, production-eligible, automatically crawlable entries with a non-null schedule receive UTC interval slots. Redis deduplicates a source/slot atomically, while `(source_id, idempotency_key)` remains the database concurrency guard. Missed slots are not backfilled automatically.

## Current limitations

The Redis-backed worker loop, admin upload/manual enqueue boundary, environment-bound registry synchronization, opt-in scheduler, ingestion operations dashboard, reviewer/publisher console, and bounded text-first PDF extraction are implemented. OCR remains intentionally out of MVP scope. A production authentication adapter, source-specific production adapters, approved production source entries, and reviewed production content are not implemented. Worker, publication, and indexing operations are documented in [worker.md](./worker.md), [publication.md](./publication.md), and [indexing.md](./indexing.md). PostgreSQL lifecycle/index eligibility has live integration coverage; full external-source staging exercises remain gated on source approval.
