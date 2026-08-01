# Uzbekistan OS MVP

Evidence-backed, multilingual guidance for navigating official Uzbekistan procedures.

## Repository status

The repository foundation, persistence slice, and first nine safe-ingestion slices are in place. The runnable system contains a responsive Next.js shell and reviewer console, a FastAPI service with versioned health and fail-closed authenticated administration endpoints, prioritized review-queue and checksum-verified artifact reads, a Redis Stream ingestion worker with stale recovery and delayed retries, environment-bound source-registry synchronization, opt-in deterministic crawl scheduling, local infrastructure definitions, executable contracts, design tokens, PostgreSQL/pgvector models, versioned knowledge tables, deterministic seeds, Alembic migrations, a schema-backed source registry, exact-URL fetching, immutable local/S3-compatible evidence storage, heading/page-preserving HTML, text, and PDF extraction artifacts, change detection, idempotent database-authoritative retry/dead-letter semantics, role-gated reviewer transitions, provider-neutral principal/role mapping, section-level comparison, transactional evidence-bound publication, and immutable audit events. An approved token-verifier adapter, approved production sources and source-specific adapters, reviewer publication/expiry/re-index controls, and infrastructure-backed integration tests are next; product workflows and retrieval follow.

See [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) for the full delivery roadmap,
[docs/phase-1-acceptance.md](./docs/phase-1-acceptance.md) and
[docs/phase-2-acceptance.md](./docs/phase-2-acceptance.md) for phase evidence,
[docs/product/launch-workflows.md](./docs/product/launch-workflows.md) for the
approved 15-flow MVP portfolio,
and [docs/decisions/OPEN_DECISIONS.md](./docs/decisions/OPEN_DECISIONS.md) for
decisions that require accountable owners.

## Prerequisites

- Node.js 24+
- pnpm 11+
- Python 3.12+
- Docker with Compose (for the complete local stack)

## Web setup

```bash
pnpm install
pnpm dev
```

The application is served at `http://localhost:3000`.

The internal reviewer console is available at `http://localhost:3000/admin/reviews`. It remains fail-closed until a reviewed token-verifier adapter and authorized principal are configured.

## API setup

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip==26.2
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`. Liveness is available at `/health` and `/api/v1/health`; dependency-aware readiness is available at `/ready` and `/api/v1/ready`.

Apply the PostgreSQL foundation migration after the database is available:

```bash
python -m alembic -c alembic.ini upgrade head
```

Database operating procedures are documented in [docs/runbooks/database.md](./docs/runbooks/database.md).

The development source registry is intentionally ineligible for production crawling. Its policy and operations are documented in [data/sources/README.md](./data/sources/README.md), [docs/runbooks/ingestion.md](./docs/runbooks/ingestion.md), [docs/runbooks/worker.md](./docs/runbooks/worker.md), [docs/runbooks/publication.md](./docs/runbooks/publication.md), and [docs/runbooks/admin-api.md](./docs/runbooks/admin-api.md).

## Complete local stack

Copy `.env.example` to `.env`, then run:

```bash
docker compose up --build
```

This starts PostgreSQL with pgvector, applies migrations, synchronizes the development registry, then starts the web app, API, worker, scheduler, Redis, and MinIO. Local credentials in `.env.example` are development-only. The committed registry contains no schedulable production source, so the scheduler remains idle by design.

Staging uses immutable GHCR images, a protected GitHub environment, automatic smoke tests, and previous-release rollback. Host preparation and activation are documented in [docs/runbooks/staging.md](./docs/runbooks/staging.md).

## Validation

```bash
pnpm lint
pnpm typecheck
pnpm build
pnpm format:check
pnpm audit --audit-level=high

cd apps/api
python -m ruff format --check . ../../scripts/validate_contracts.py
python -m ruff check .
python -m pytest
python -m pip_audit --skip-editable
```

## Architecture principles

- Retrieval first: answers must be bounded by eligible, verified evidence.
- Contract first: OpenAPI and JSON Schema define service boundaries.
- Provider independent: external AI and storage providers sit behind adapters.
- Auditable: source snapshots, document versions, prompts, retrievals, citations, and reviews retain lineage.
- Accessible and multilingual: WCAG 2.2 AA and English, Uzbek, and Russian are baseline requirements.
