# Decision register

Open decisions block later milestones but do not block the repository foundation.
Accepted decisions link to the record that defines their consequences and evidence.

| ID    | Decision                | Status                                  | Owner                    | Record / recommended baseline                                                                                                                                                            |
| ----- | ----------------------- | --------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D-001 | Launch workflows        | Accepted 2026-08-01                     | Product + domain         | ADR 0014 and `docs/product/launch-workflows.md`: 15 initial workflows                                                                                                                    |
| D-002 | Citation metric         | Open                                    | Product + AI             | ADR 0022 and `phase-4-gates.v1.json` implement separate claim coverage and citation-validity metrics; approve or revise the proposed 95%/98% release thresholds after the first live run |
| D-003 | Customer authentication | Accepted 2026-08-10; amended 2026-08-11 | Product + security       | ADR 0023: account-required assistant; email/password primary, international phone/password with SMS confirmation secondary; Google/Apple and OneID deferred                              |
| D-004 | Translation policy      | Open                                    | Content + domain         | Human review required for published procedural guidance                                                                                                                                  |
| D-005 | Freshness policy        | Open                                    | Content + domain         | Review interval and expiry behavior by risk level                                                                                                                                        |
| D-006 | Model routing           | Open                                    | AI + platform            | ADR 0020 proposes Terra/low for grounded generation behind a disabled route; approve only after frozen multilingual quality, latency, and cost gates                                     |
| D-007 | Production hosting      | Open                                    | Platform + security      | Managed regional services with encrypted backups                                                                                                                                         |
| D-008 | Privacy/retention       | Open                                    | Product + legal/security | Minimize PII; define deletion, analytics consent, and retention before alpha                                                                                                             |
| D-009 | Dark mode               | Accepted 2026-08-01                     | Design + product         | ADR 0015: system default plus persistent explicit override in MVP                                                                                                                        |
| D-010 | Reliability             | Accepted 2026-08-01                     | Platform + product       | ADR 0016: 99.9% public SLO, one-hour database RPO, four-hour database RTO                                                                                                                |

ADR 0023 resolves the customer-facing provider and session model. The provider-neutral administrative identity boundary remains fail-closed until a Supabase JWT verifier, role mapping, and recovery operations are separately configured and approved.

## Required decision record

For each decision, record context, options considered, chosen option, consequences, owner, approval date, and the artifacts that must change.
