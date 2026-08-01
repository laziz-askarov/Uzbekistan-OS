# Uzbekistan OS MVP

Evidence-backed, multilingual guidance for navigating official Uzbekistan procedures.

## Repository status

The repository foundation, persistence slice, and first three safe-ingestion slices are in place. The runnable system contains a responsive Next.js shell, a FastAPI service with versioned health endpoints, local infrastructure definitions, initial contracts, design tokens, PostgreSQL/pgvector models, versioned knowledge tables, deterministic seeds, Alembic migrations, a schema-backed source registry, exact-URL fetching, immutable local/S3-compatible evidence storage, heading-preserving extraction artifacts, change detection, idempotent retry/dead-letter semantics, a review queue, role-gated reviewer transitions, section-level comparison, and immutable audit events. Authentication middleware/routes, production source adapters, transactional publication, and the worker loop are next; product workflows and retrieval follow.

See [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) for the full delivery roadmap and [docs/decisions/OPEN_DECISIONS.md](./docs/decisions/OPEN_DECISIONS.md) for decisions that require accountable owners.

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

## API setup

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`; health is available at `/health` and `/api/v1/health`.

Apply the PostgreSQL foundation migration after the database is available:

```bash
python -m alembic -c alembic.ini upgrade head
```

Database operating procedures are documented in [docs/runbooks/database.md](./docs/runbooks/database.md).

The development source registry is intentionally ineligible for production crawling. Its policy and ingestion operations are documented in [data/sources/README.md](./data/sources/README.md) and [docs/runbooks/ingestion.md](./docs/runbooks/ingestion.md).

## Complete local stack

Copy `.env.example` to `.env`, then run:

```bash
docker compose up --build
```

This starts the web app, API, PostgreSQL with pgvector, Redis, and MinIO. Local credentials in `.env.example` are development-only.

## Validation

```bash
pnpm lint
pnpm typecheck
pnpm build

cd apps/api
python -m ruff check .
python -m pytest
```

## Architecture principles

- Retrieval first: answers must be bounded by eligible, verified evidence.
- Contract first: OpenAPI and JSON Schema define service boundaries.
- Provider independent: external AI and storage providers sit behind adapters.
- Auditable: source snapshots, document versions, prompts, retrievals, citations, and reviews retain lineage.
- Accessible and multilingual: WCAG 2.2 AA and English, Uzbek, and Russian are baseline requirements.
