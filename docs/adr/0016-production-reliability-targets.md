# ADR 0016: Cost-conscious production reliability targets

Date: 2026-08-01

Status: Accepted

Decision: D-010

## Context

The MVP needs measurable reliability and recovery targets before production
architecture and backup choices can be evaluated. Active-active multi-region
infrastructure would add disproportionate cost and operational complexity at this
stage, while daily-only database recovery would expose too much reviewed knowledge,
workflow state, and audit history.

## Decision

### Service-level objectives

Measured monthly, excluding approved maintenance announced at least 48 hours ahead:

| Signal | MVP target | Measurement boundary |
| --- | --- | --- |
| Public web and non-streaming API availability | 99.9% | Valid requests that do not return an infrastructure-caused 5xx or timeout |
| Reviewer/admin availability | 99.5% | Authenticated internal requests that do not return an infrastructure-caused 5xx or timeout |
| Non-streaming API latency | p95 ≤ 750 ms | Server receipt through completed response, excluding client network time |
| Chat stream start | p95 ≤ 2 seconds | Server receipt through application-owned `start` SSE event |
| First supported chat content | p95 ≤ 5 seconds | Server receipt through first validated `chunk`, including configured model provider |
| Web Core Vitals | p75 LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 | Production real-user monitoring by page group |
| Scheduled ingestion completion | 95% within 6 hours | Due time through successful validated artifact or explicit terminal failure |

A 99.9% monthly availability target provides an error budget of approximately 43
minutes and 50 seconds in a 30-day month. Exhausting 75% of that budget pauses
non-essential production releases; exhausting 100% limits releases to reliability
and security work until the rolling window recovers.

### Recovery objectives

| State or service | RPO | RTO | Cost-conscious control |
| --- | --- | --- | --- |
| Stateless web, API, worker, and scheduler | 0 | 1 hour | Immutable images and configuration in Git; redeploy into one primary region |
| PostgreSQL knowledge, identity, workflow, and audit data | 1 hour | 4 hours | Managed backups plus point-in-time recovery, seven-day PITR window, 30-day daily-backup retention |
| Immutable evidence objects | 24 hours | 8 hours | Object versioning, checksum inventory, daily backup/lifecycle copy; republish remains blocked until evidence verifies |
| Redis cache and stream transport | Not applicable | 2 hours | Treat as disposable transport; reconstruct work from database-authoritative job state |

Recovery is declared successful only after schema version, critical row counts,
retrieval eligibility, evidence checksums, authentication, and smoke tests pass.

### Operating model

- Use one managed primary region for the MVP; do not fund active-active multi-region
  infrastructure before traffic or error-budget evidence justifies it.
- Run at least two public web/API instances in production and autoscale on measured
  saturation. Internal and background services may scale from one when durable state
  remains outside the process.
- Encrypt backups and evidence at rest and in transit. Restrict restore authority and
  log every recovery operation.
- Exercise a PostgreSQL restore monthly and a full service recovery quarterly.
- Review the objectives after 90 days of production traffic or after any severity-one
  incident, whichever occurs first.

## Consequences

- D-010 is resolved for MVP architecture and operational acceptance.
- Staging may use fewer replicas, but it must exercise the same backup, restore, and
  deployment paths.
- Provider and planned-maintenance exclusions must remain visible in reporting; they
  cannot be used to hide application failures.
- Tighter objectives require an explicit cost and architecture review.
