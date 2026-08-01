# Worker

The ingestion core now defines source eligibility, exact-URL fetching, normalization, content-addressed local/S3 storage, heading-preserving extraction artifacts, change detection, review-queue creation, idempotent job claims, bounded retries, and dead-letter states in `apps/api/app/ingestion`. The shared logic is kept independent of FastAPI routes so this deployable can call it without duplicating business rules.

The worker process and Redis queue consumer remain intentionally absent until the first production sources, scheduling policy, and deployment ownership are approved. See `docs/adr/0004-safe-idempotent-ingestion-boundary.md` and `docs/runbooks/ingestion.md`.
