# Repository guidance

## Scope

- The MVP domains are Immigration, Tourism, Business Registration, Healthcare, and Everyday Living.
- Do not add voice, OCR, appointments, payments, native apps, reminders, autonomous agents, direct government API integrations, or user document storage without an approved scope change.
- Internal storage of official-source snapshots and ingestion evidence is allowed.

## Architecture

- Keep deterministic business rules, authorization, publication eligibility, and citation validation in the API layer.
- Treat generated model output as untrusted until it passes schema and evidence validation.
- Never retrieve unpublished, expired, unsupported, or inapplicable knowledge.
- Keep external providers behind interfaces and configuration; do not embed provider or model choices in domain logic.

## Engineering

- Add or update tests with every behavior change.
- Keep OpenAPI, runtime models, and generated clients synchronized.
- Use structured logs and propagate request IDs across service boundaries.
- Do not commit secrets, local environment files, generated build output, or production data.
- Preserve accessibility and localization behavior in every UI change.

## Validation

- Web: `pnpm lint && pnpm typecheck && pnpm build`
- API: from `apps/api`, run `python -m ruff check . && python -m pytest`
- Contracts: validate `packages/contracts/openapi.yaml` and JSON Schemas before merging contract changes.

