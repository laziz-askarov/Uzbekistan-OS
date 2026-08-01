# Worker

The first ingestion slice now defines source eligibility, exact-URL fetching, normalization, content-addressed snapshots, change detection, idempotent job claims, bounded retries, and dead-letter states in `apps/api/app/ingestion`. The shared logic is kept independent of FastAPI routes so this deployable can call it without duplicating business rules.

The worker process and Redis queue consumer remain intentionally absent until the first production sources, scheduling policy, and deployment ownership are approved. See `docs/adr/0004-safe-idempotent-ingestion-boundary.md` and `docs/runbooks/ingestion.md`.
