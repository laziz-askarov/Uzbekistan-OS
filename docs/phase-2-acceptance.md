# Phase 2 acceptance record

Date assessed: 2026-08-01

## Scope

Phase 2 establishes the contracts, data model, knowledge schemas, design system,
and product-flow specifications that later implementation phases consume. A
feature implemented ahead of schedule does not close its Phase 2 dependency
unless the corresponding contract and acceptance evidence are checked in.

## Deliverable status

| Phase 2 requirement                                       | Repository evidence                                                                                                                                                                                                                                                     | Status                                                                                                            |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| OpenAPI 3.1 contract                                      | `packages/contracts/openapi.yaml` covers authentication, profiles, conversation/chat lifecycle, knowledge/search/source browsing, workflows/progress, feedback, ingestion, and administration; planned operations are explicitly marked                                 | Complete as a planned contract; implemented operations remain runtime-compatibility tested                        |
| Response/error envelopes and cursor pagination            | ADR 0012 plus shared response metadata, typed success/error envelopes, request identifiers, cursor and limit parameters, and validator enforcement                                                                                                                       | Complete for the planned contract surface                                                                         |
| Authorization matrix and idempotency rules                | ADR 0012 plus machine-readable `x-authorization` on every operation and `x-idempotency` on every mutation                                                                                                                                                               | Complete for the Phase 2 contract surface                                                                         |
| Universal knowledge JSON Schema                           | `knowledge-document.schema.json` defines lifecycle, versions, sections, citations, sources, entities, applicability, requirements, ordered steps, fees, and translation status; constrained extension schemas and positive/negative fixtures cover all five MVP domains | Complete for the Phase 2 contract surface                                                                         |
| Extraction artifact JSON Schema                           | `extraction-artifact.schema.json` and a validated non-production fixture                                                                                                                                                                                                | Complete for the current text-first extraction boundary                                                           |
| PostgreSQL schemas and initial migrations                 | Namespaced SQLAlchemy metadata and Alembic migrations `0001` through `0005`, with constraints, indexes, deterministic seeds, compiled upgrade/downgrade tests, an exercised `0005 -> 0004 -> 0005` drill, and the row-access decision in ADR 0013                       | Complete for the current Phase 2 bounded contexts                                                                 |
| Backup and restoration procedure                          | `docs/runbooks/database.md`, `scripts/drill_database_restore.sh`, and ADR 0016; the isolated restore, count comparison, retrieval-view query, downgrade, and re-upgrade passed on 2026-08-01                                                                              | Complete; production target is one-hour database RPO and four-hour database RTO                                    |
| Design tokens synchronized with application styles        | `packages/design-system/tokens.css` is imported by the application; `tailwind.css` provides the Tailwind v4 bridge; ADR 0015 and the accessible catalogue toggle implement system-aware light and dark MVP modes                                                        | Complete for both approved MVP appearance modes                                                                    |
| Accessible core components and documentation              | Reusable React button, field, select, card, alert, badge, and stack primitives; component styles, accessibility contract, live `/design-system` catalogue, and `scripts/validate_design_system.py`                                                                         | Complete for the reusable Phase 2 component baseline                                                               |
| Responsive wireframes and launch-flow acceptance criteria | `docs/product/responsive-flow-wireframes.md`, `docs/product/launch-workflows.md`, and ADR 0014 define the approved 15-flow portfolio, mobile/tablet/desktop topology, surface criteria, and per-flow implementation-readiness template                                      | Complete for Phase 2 product specification                                                                         |

## Ordered completion slices

1. Complete OpenAPI conventions and the planned MVP operation surface.
2. Expand the universal knowledge schema and add domain-extension fixtures.
3. Record row-level-access decisions and prove migration downgrade and backup restoration.
4. Build reusable accessible core components and component documentation.
5. Check in responsive launch-flow wireframes and acceptance criteria.
6. Run the complete Phase 2 exit-gate suite and record the checkpoint CI run.

## Exit gate

Phase 2 closes only when all of the following pass:

- OpenAPI validation and runtime compatibility for implemented operations.
- Valid and intentionally invalid fixtures for every knowledge schema.
- Forward and supported rollback migration tests.
- A recorded PostgreSQL backup restoration drill.
- Automated accessibility smoke tests for reusable core components.
- Reviewed mobile, tablet, and desktop acceptance criteria for every approved
  launch flow.

The Phase 2 product decisions for the initial workflow portfolio, MVP appearance
modes, and reliability/recovery targets are accepted in ADRs 0014–0016.

## Validation record

The technical Phase 2 exit gate passed locally on 2026-08-01:

- 87 API tests passed.
- OpenAPI, authorization, idempotency, reference, SSE-event, universal knowledge,
  domain-extension, and extraction-artifact contracts validated.
- Ruff format/lint, Prettier, ESLint, TypeScript, and the production Next.js build
  passed.
- Alembic upgrade SQL compiled through `20260731_0005`; the isolated database
  backup/restore and `0005 -> 0004 -> 0005` drill passed.
- Local and staging Compose configurations and all shell scripts validated.
- Browser checks passed at 1280px, 390px, and 320px reflow widths: no horizontal
  overflow, all rendered controls met the 44px minimum, semantic regions and
  connected error descriptions were present, the native select worked, and the
  console had no warnings or errors.
- Light/dark interaction checks passed: the labelled toggle updated semantic
  colors, `color-scheme`, and `aria-pressed`, persisted the explicit preference
  across reload, and dark mode passed 320px reflow with no console issues.

The final repository gate is a committed `staging` checkpoint with a passing GitHub
CI run. Flow-specific authoritative sources, localized content, and implementation
screenshots are later launch-readiness evidence rather than Phase 2 blockers.
