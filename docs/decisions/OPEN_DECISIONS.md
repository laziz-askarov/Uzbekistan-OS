# Decision register

Open decisions block later milestones but do not block the repository foundation.
Accepted decisions link to the record that defines their consequences and evidence.

| ID | Decision | Status | Owner | Record / recommended baseline |
| --- | --- | --- | --- | --- |
| D-001 | Launch workflows | Accepted 2026-08-01 | Product + domain | ADR 0014 and `docs/product/launch-workflows.md`: 15 initial workflows |
| D-002 | Citation metric | Open | Product + AI | Measure claim-level coverage and source validity separately |
| D-003 | Authentication | Open | Product + security | Guest and email/password first; gate Google OAuth separately |
| D-004 | Translation policy | Open | Content + domain | Human review required for published procedural guidance |
| D-005 | Freshness policy | Open | Content + domain | Review interval and expiry behavior by risk level |
| D-006 | Model routing | Open | AI + platform | Configurable generation, embedding, and reranking roles with evaluation gates |
| D-007 | Production hosting | Open | Platform + security | Managed regional services with encrypted backups |
| D-008 | Privacy/retention | Open | Product + legal/security | Minimize PII; define deletion, analytics consent, and retention before alpha |
| D-009 | Dark mode | Accepted 2026-08-01 | Design + product | ADR 0015: system default plus persistent explicit override in MVP |
| D-010 | Reliability | Accepted 2026-08-01 | Platform + product | ADR 0016: 99.9% public SLO, one-hour database RPO, four-hour database RTO |

The provider-neutral identity model and fail-closed Bearer verification boundary do not resolve D-003. The selected login/token provider, verification adapter, session lifecycle, and account-recovery policy still require product and security approval.

## Required decision record

For each decision, record context, options considered, chosen option, consequences, owner, approval date, and the artifacts that must change.
