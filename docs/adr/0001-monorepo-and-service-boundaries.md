# ADR 0001: Monorepo and initial service boundaries

- Status: Accepted for foundation
- Date: 2026-07-31

## Context

The MVP combines a TypeScript web application, Python API and workers, shared API/knowledge contracts, and local infrastructure. The specifications require independent scaling later but do not justify distributed-service complexity at project start.

## Decision

Use one monorepo with three deployable boundaries: web, API, and background worker. Keep AI orchestration, retrieval, knowledge validation, crawler adapters, and database code as modular packages until operational evidence justifies independent services.

## Consequences

- Contracts and cross-language changes can be reviewed together.
- Local setup and CI remain manageable.
- Package boundaries must be enforced to prevent a monolith without internal structure.
- A package may become a service only after a documented scaling, security, or ownership need.

