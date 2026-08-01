# Uzbekistan OS MVP Execution Plan

> Implementation status (2026-07-31): the Phase 1 foundation, first Phase 2
> database slice, and first two Phase 3 ingestion slices are complete. The
> schema-backed source registry, crawl-eligibility rules, exact-URL fetch port,
> deterministic HTML/text normalization, content-addressed snapshot storage,
> change detection, idempotent jobs, bounded retry/dead-letter states,
> S3-compatible evidence storage, structured extraction artifacts, and review
> queue persistence are implemented. No real source is authorized yet. Docker-backed migration and
> restore drills remain pending because Docker is unavailable in this workspace.
> The next delivery slice is production source approval/adapters, the worker
> loop, authenticated reviewer actions, comparison, and transactional publication.

## 1. Executive summary

The project began as a specification-only greenfield initiative. It now has a working monorepo foundation, executable contracts, database migrations, and the first fail-closed ingestion boundary; product decisions, approved source inventory, production infrastructure, reviewer tooling, retrieval, workflows, and benchmark data remain incomplete.

The recommended delivery approach is a 16-week MVP program for an 8-10 person cross-functional team. Build one complete, evidence-backed vertical slice first, prove retrieval and citation quality, then expand content and workflows across the five PRD domains. Treat knowledge quality and evaluation as product-critical workstreams rather than post-build QA.

The critical path is:

`scope decisions -> contracts and schemas -> migrations -> ingestion -> verified knowledge -> hybrid retrieval -> cited chat -> evaluation gates -> beta -> production`

Frontend, design-system, content acquisition, and platform work can run in parallel after contracts stabilize.

## 2. Reconciled MVP boundary

### Included

- Responsive web application with English, Uzbek, and Russian support.
- Guest sessions and optional user accounts.
- Streaming AI chat grounded only in eligible, verified knowledge.
- Official-source citations, confidence/status messaging, and feedback.
- Search and document/source browsing.
- Guided workflows, progress tracking, and personalized checklists.
- User profile/preferences and conversation continuity.
- Admin/reviewer flow for ingestion, validation, publication, and audit.
- Five product domains: Immigration, Tourism, Business Registration, Healthcare, and Everyday Living.
- At least 200 published structured knowledge documents.

### Excluded

- Voice, OCR, appointments, payments, native mobile apps, reminders, autonomous agents, direct government API integrations, and user document storage.
- The TDD's Banking, Transportation, Housing, Education, Legal, and Taxation list is a future-compatible taxonomy, not authorization to expand the MVP. Everyday Living may reference a tightly scoped subset only when needed for approved launch workflows.
- Internal object storage for crawler snapshots and ingestion evidence is allowed; user-facing document storage remains out of scope.

## 3. Decisions required before implementation

Resolve and record these as Architecture Decision Records (ADRs) in week 1:

1. **Launch workflows:** choose 10-15 high-value user journeys and rank them by demand, risk, and source availability.
2. **Citation metric:** define whether 95% means response-level citation presence, factual-claim coverage, or citation correctness. Recommended release gate: at least 95% factual-claim coverage and at least 98% citation-source validity on the benchmark set.
3. **Authentication:** confirm email/password plus guest as baseline; decide whether Google OAuth is launch-critical or post-MVP.
4. **Translation policy:** decide which language is canonical, who approves translations, and whether machine-assisted translations can be published without human review. Recommended: no unreviewed translated procedural guidance in production.
5. **Freshness policy:** set review intervals and expiry behavior by domain/risk level.
6. **AI providers:** select generation, embedding, and reranking providers behind interfaces; define fallbacks, budgets, and data-processing requirements.
7. **Deployment target:** choose cloud, region, managed PostgreSQL/Redis/object storage, secrets manager, and production support model.
8. **Privacy and retention:** define PII categories, conversation retention, deletion/export behavior, analytics consent, and audit retention.
9. **Dark mode:** build token support from day one; include the theme in MVP only if it passes the same accessibility and visual QA gates.
10. **Availability target:** replace “high availability” with measurable launch SLOs and recovery objectives.

## 4. Target implementation shape

Use a monorepo matching the TDD:

```text
apps/
  web/                 Next.js web application
  api/                 FastAPI public/internal API
  worker/              ingestion, embedding, and background jobs
packages/
  contracts/           OpenAPI-generated clients and shared schemas
  database/            SQLAlchemy models, Alembic migrations, seeds
  knowledge/           JSON Schema, validators, examples
  ai/                  orchestration, prompts, model gateway, validation
  rag/                 indexing, retrieval, reranking, evidence packs
  crawler/             source adapters, parsing, snapshots, change detection
  design-system/       tokens, React components, accessibility tests
  observability/       logging, metrics, tracing helpers
data/
  sources/              approved source registry
  fixtures/             safe development fixtures
  evaluations/          benchmark questions and expected evidence
docs/
  adr/                  architecture decisions
  runbooks/             operations and incident procedures
  product/              flows, acceptance criteria, content policy
infra/                  local, staging, and production definitions
scripts/                repeatable developer and operational commands
```

PostgreSQL with pgvector is the system of record. Redis supports ephemeral sessions, queues, rate limits, and safe caches. Object storage holds internal raw snapshots and extraction artifacts. The API owns orchestration and streams responses with Server-Sent Events (SSE). Business rules, publication eligibility, permissions, and citation validation remain deterministic server-side logic.

## 5. Sixteen-week roadmap

### Phase 0 - Product and risk closure (week 1)

**Deliverables**

- Approved MVP domain/workflow matrix and prioritized user stories.
- Definition of the 200-document target by domain, language, source, and workflow.
- Decision log for all items in section 3.
- Threat model and data classification.
- Measurable SLOs, quality metrics, and launch gates.
- Initial official-source registry with owners and crawl permissions.

**Exit gate:** product, domain, engineering, design, and security owners sign off on scope and metrics.

### Phase 1 - Repository and engineering foundation (weeks 1-2)

**Deliverables**

- Git repository and monorepo scaffold; development conventions and ownership rules.
- Reproducible local stack for web, API, worker, PostgreSQL/pgvector, Redis, and object storage.
- CI for format, lint, type-check, unit tests, dependency scanning, migration checks, and builds.
- Environment configuration, secret-handling rules, structured logging, request IDs, and health/readiness endpoints.
- Staging skeleton with automated deployments and rollback.

**Exit gate:** a new developer can bootstrap the stack from documentation; CI and a staging smoke test pass.

### Phase 2 - Contracts, data model, and design foundations (weeks 2-4)

**Deliverables**

- OpenAPI 3.1 contract for auth, profiles, conversations, chat/SSE, knowledge, search, workflows, feedback, ingestion, and admin APIs.
- Standard response/error envelopes, cursor pagination, authorization matrix, and idempotency rules.
- JSON Schema for universal knowledge objects, domain extensions, entities, requirements, steps, fees, applicability, translations, versions, and citations.
- PostgreSQL schemas, constraints, indexes, row-level access decisions, initial migrations, seeds, and backup/restore procedure.
- CSS custom-property token source synchronized with Tailwind; accessible core components and Storybook-style documentation.
- Wireframes and acceptance criteria for all launch flows across mobile, tablet, and desktop.

**Exit gate:** contract tests, schema fixtures, migration up/down tests, accessibility smoke tests, and backup restoration pass.

### Phase 3 - Knowledge ingestion vertical slice (weeks 3-6)

**Current progress:** registry validation, fetch/snapshot ports, HTML/text normalization, change detection, job idempotency, bounded retries, dead-letter states, S3-compatible storage, heading-preserving extraction artifacts, review-queue persistence, and lineage metadata are implemented against a non-production fixture. Production sources, the worker loop, reviewer decision APIs/UI, PDF adapters, transactional publication, and embeddings remain.

**Deliverables**

- Approved source registry and per-source crawl/fetch adapters.
- Snapshotting, extraction, normalization, structured parsing, validation, deduplication, change detection, and review queue.
- Immutable versions, publication states, supersession, effective dates, applicability filters, and audit history.
- Semantic chunker that preserves headings, procedures, complete concepts, and citation provenance.
- Embedding/index jobs with retries, idempotency, dead-letter handling, and cost/latency telemetry.
- Reviewer UI/API for compare, approve, reject, publish, expire, and re-index actions.
- First 20 production-quality documents covering one low-risk and one higher-risk workflow in all supported languages.

**Exit gate:** source-to-published-index lineage is reproducible and auditable; ineligible or expired content cannot be retrieved.

### Phase 4 - Retrieval, AI orchestration, and evaluation (weeks 4-8)

**Deliverables**

- Language detection, intent/entity extraction, query rewriting, risk classification, and retrieval planning with typed outputs.
- Hybrid PostgreSQL full-text + pgvector retrieval, metadata/applicability filters, reranking, and evidence-pack construction.
- Layered prompt registry with versioning, model gateway, timeouts, retries, budgets, and structured response schema.
- Citation and evidence validator that rejects unsupported factual claims or degrades safely to an insufficiency response.
- Prompt-injection defenses for user input and retrieved content; PII-safe logging.
- Conversation history, structured context state, and bounded summaries.
- Evaluation harness containing golden questions, expected sources, adversarial prompts, multilingual cases, and abstention cases.

**Exit gate:** offline retrieval, groundedness, citation, safety, multilingual, latency, and cost thresholds pass for the initial workflows.

### Phase 5 - Public API and product workflows (weeks 5-9)

**Deliverables**

- Guest/user authentication, token rotation/revocation, profile and preference endpoints.
- Conversation lifecycle, soft deletion, message persistence, feedback, and audit behavior.
- SSE contract supporting start, chunk, citation, workflow, done, and error events, including reconnect/cancellation handling.
- Knowledge search/document/source endpoints with filters and cursor pagination.
- Workflow definitions, dependencies, personalized checklist generation, progress persistence, and timeline/requirements APIs.
- Admin authorization and moderation endpoints.

**Exit gate:** generated client contract tests, authz tests, integration tests, concurrency tests, and SSE failure-mode tests pass.

### Phase 6 - User experience implementation (weeks 5-10)

**Deliverables**

- Responsive application shell: desktop left navigation/context panel and mobile bottom navigation/context sheets.
- AI assistant with streaming, stop/retry, structured answer sections, citations, warnings, related questions, and feedback.
- Search, document/source detail, workflow list/detail/progress, checklist, history, profile, settings, and saved-item experiences.
- Localized UI and content direction/format handling for English, Uzbek, and Russian.
- Skeletons, empty states, recoverable errors, offline/interrupted-stream behavior, and safe insufficient-evidence states.
- Keyboard navigation, visible focus, semantic structure, screen-reader announcements, 44px touch targets, reduced motion, zoom/reflow, and contrast compliance.

**Exit gate:** end-to-end tests for every critical flow pass at target breakpoints, with zero critical WCAG 2.2 AA findings.

### Phase 7 - Content scale-up and quality operations (weeks 6-12)

**Deliverables**

- At least 200 reviewed and published documents allocated across the five domains and launch workflows.
- Every factual claim linked to official evidence; translation and freshness statuses visible.
- Domain-owner review process, service-level expectations, sampling audits, expiry alerts, and correction workflow.
- Benchmark expanded to cover every launch workflow, language, risk level, and common ambiguity.
- Knowledge quality dashboard for completeness, freshness, citation coverage, translation coverage, and failed ingestion jobs.

**Exit gate:** content inventory and quality targets pass; no launch workflow depends on missing, expired, or unreviewed knowledge.

### Phase 8 - Hardening and private alpha (weeks 10-14)

**Deliverables**

- Full unit, integration, contract, migration, end-to-end, accessibility, security, and load test suites.
- Red-team tests for prompt injection, data exfiltration, poisoned retrieval, unsupported claims, unsafe advice, and privilege escalation.
- Performance work against first-token and total-response targets at representative concurrent load.
- Dashboards and alerts for availability, latency, errors, retrieval quality, model usage/cost, ingestion health, and citation failures.
- Backup/restore, disaster recovery, rollback, key rotation, incident response, and content-correction drills.
- Private alpha with instrumented usability sessions across target user groups and languages.

**Exit gate:** no open critical/high security defects, no release-blocking accessibility defects, SLO tests pass, and recovery drills meet objectives.

### Phase 9 - Beta, launch, and stabilization (weeks 14-16)

**Deliverables**

- Controlled beta with feature flags, rate limits, support workflow, and daily quality review.
- Final acceptance against product metrics and benchmark gates.
- Production deployment, synthetic monitoring, on-call schedule, incident channels, and launch rollback decision tree.
- Two-week stabilization backlog prioritized by user harm, reliability, and workflow completion impact.

**Exit gate:** product, engineering, content, security, and operations owners approve production release.

## 6. Workstreams and accountable owners

| Workstream | Accountable role | Core outputs |
|---|---|---|
| Product/domain | Product lead + Uzbekistan domain lead | Scope, workflows, metrics, source policy, acceptance |
| Architecture/platform | Tech lead + platform engineer | ADRs, repository, environments, CI/CD, SLOs |
| Backend/data | Two backend engineers | API, auth, models, migrations, workflows, admin |
| AI/RAG | Two AI/search engineers | orchestration, retrieval, prompts, validation, evaluation |
| Knowledge operations | Content lead + 2-3 researchers/reviewers | source registry, 200 documents, translations, freshness |
| Web/design system | Two frontend engineers + product designer | tokens, components, responsive/localized experiences |
| Quality/security | QA/SDET + fractional security reviewer | automation, accessibility, load, threat validation, release gates |

The minimum practical team is about eight full-time contributors plus domain, design, and security support. With fewer than six contributors, reduce launch workflows or plan for a longer schedule; do not preserve scope by reducing knowledge review or evaluation.

## 7. Test and release matrix

| Layer | Required evidence |
|---|---|
| Schemas/contracts | JSON/OpenAPI validation, generated-client compatibility, breaking-change checks |
| Database | migration forward/rollback, constraints, index plans, isolation, backup restoration |
| Ingestion | idempotency, retry/dead-letter, change detection, provenance, publication eligibility |
| Retrieval | recall@k, MRR/nDCG, applicability precision, expired-content exclusion, multilingual coverage |
| Generation | groundedness, claim-level citation coverage, citation validity, abstention, schema validity |
| Security | authn/authz, rate limiting, injection, poisoned content, secret/PII leakage, dependency/container scans |
| Frontend | unit/component, visual regression, end-to-end, browser/device, localization, interrupted streams |
| Accessibility | automated checks plus keyboard and screen-reader manual audits against WCAG 2.2 AA |
| Performance | first token, total latency, throughput, database/vector query latency, queue lag, cost/request |
| Operations | deploy/rollback, alert routing, backup/restore, model outage, crawler failure, content correction |

## 8. Launch scorecard

Define exact sample sizes and confidence intervals in week 1. Recommended minimum gates:

- 200+ verified, published structured documents.
- 95%+ factual-claim citation coverage and 98%+ citation validity on the frozen benchmark.
- Zero retrieval of expired, unpublished, unsupported, or inapplicable content in release tests.
- First SSE content event p95 under 3 seconds and completed response p50 under 8 seconds under agreed load; track p95 separately.
- 99.9% monthly API availability target after launch, with explicit exclusions and error-budget policy.
- Zero critical/high unresolved security findings.
- Zero critical accessibility findings and documented WCAG 2.2 AA audit.
- Successful completion rate defined per launch workflow and measured in beta.
- Per-request model cost budget and alert threshold approved before beta.
- Backup restoration and rollback demonstrated in staging.

## 9. Major risks and controls

| Risk | Control |
|---|---|
| Scope expands from five to ten domains | Signed domain/workflow matrix; taxonomy expansion requires change control |
| “Official” sources conflict or become stale | Source precedence policy, snapshots, effective dates, expiry, human review |
| 200 documents become a vanity metric | Allocate documents to user journeys and require completeness/citation quality gates |
| Multilingual quality trails English | Per-language benchmarks, native reviewers, explicit translation status and fallback |
| Hallucinated or misplaced citations | Evidence-only generation, claim-level validator, abstention, citation audits |
| Crawler fragility blocks freshness | Source adapters, change detection, retry/dead-letter, manual ingestion fallback |
| Latency target conflicts with reranking/validation | Budget each pipeline stage, stream early, cache only safe deterministic artifacts |
| Sensitive data appears in chat/logs | PII minimization, redaction, retention limits, encryption, access controls |
| Admin/review tooling is deferred | Include it in the first ingestion slice; publishing without review is prohibited |
| Design breadth delays core value | Prioritize chat plus two workflows; reuse tokenized components for remaining screens |

## 10. First ten working days

1. Name accountable product, technical, content, design, security, and operations owners.
2. Approve the five-domain boundary and rank 10-15 launch workflows.
3. Create the source registry and select the first two vertical-slice workflows. **Registry contract complete; production sources and workflows still require approval.**
4. Write ADRs for repository/tooling, hosting, auth, AI providers, multilingual policy, and retention.
5. Scaffold the monorepo and local Docker stack.
6. Draft OpenAPI, knowledge JSON Schema, answer schema, SSE events, and authorization matrix.
7. Draft database ERD and initial migration sequence from the DDS schemas. **Foundation migration complete; ERD and later bounded-context migrations remain.**
8. Create 30-50 golden benchmark questions before tuning retrieval or prompts.
9. Establish design tokens and prototype the streaming/citation interaction.
10. Deploy the empty stack to staging and prove CI, migrations, observability, rollback, and backup restoration.

## 11. MVP definition of done

The MVP is complete only when the approved workflows are usable end to end in all three languages; 200+ knowledge documents are verified, current, published, and traceable; retrieval excludes ineligible knowledge; generated factual claims are evidence-backed and cited; guest/account, conversation, search, workflow, checklist, feedback, admin, and review paths work; performance, security, accessibility, recovery, and evaluation gates pass; and production operations have named owners, dashboards, alerts, runbooks, backups, and rollback procedures.
