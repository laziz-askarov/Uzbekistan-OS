# Phase 1 acceptance record

Date assessed: 2026-08-01

## Deliverable evidence

| Phase 1 requirement | Repository evidence | Status |
|---|---|---|
| Git monorepo, conventions, and ownership | `pnpm-workspace.yaml`, `AGENTS.md`, `CONTRIBUTING.md`, `.github/CODEOWNERS`, `SECURITY.md` | Complete |
| Reproducible local web/API/worker/PostgreSQL/Redis/object-store stack | Pinned service images and dependency lockfiles in `docker-compose.yml`, service Dockerfiles, deterministic migration/registry/object-store initialization | Complete in code; local Docker execution unavailable in this workspace |
| CI format, lint, typecheck, tests, dependency scanning, migration checks, contracts, and builds | `.github/workflows/ci.yml`, Ruff/Prettier configuration, `pnpm audit`, and `pip-audit` | Complete |
| Environment and secret-handling rules | `.env.example`, `infra/staging/.env.example`, `SECURITY.md`, ignored local secret files, protected-environment documentation | Complete |
| Structured logging and request IDs | `app.observability`, HTTP middleware, worker logging, and observability tests | Complete |
| Health and readiness | Liveness endpoints plus PostgreSQL/Redis/evidence-bucket readiness endpoints and tests | Complete |
| Staging deployment and rollback skeleton | Commit-SHA GHCR images, protected GitHub environment, SSH deployment, external smoke test, previous-image rollback, and empty staging registry | Complete in code |

## Exit gate

- New-developer bootstrap instructions: complete in `README.md` and `CONTRIBUTING.md`.
- Local equivalent CI checks: must pass before the Phase 1 checkpoint is committed.
- GitHub CI: must pass on the Phase 1 checkpoint.
- Live staging smoke and rollback: pending host/environment configuration and one recorded successful exercise under `docs/runbooks/staging.md`.

Phase 1 is repository-complete but not operationally closed until the final live staging exercise is recorded. No source or application change can substitute for the required host, DNS/TLS origins, SSH credentials, and GitHub environment configuration.
