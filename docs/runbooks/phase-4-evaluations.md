# Phase 4 evaluation runbook

## Checked-in artifacts

- `data/evaluations/phase-4-benchmark.v1.json` is the frozen 45-case benchmark.
- `data/evaluations/phase-4-gates.v1.json` separates approved engineering
  invariants from proposed product/AI/platform thresholds.
- `data/evaluations/runs/phase-4-planning-baseline.v1.json` records the current
  deterministic planning baseline.

Do not edit a frozen benchmark or historical run in place. Add a new version and
retain the old artifact so release evidence remains reproducible.

## Run an evaluation

From `apps/api`:

```bash
.venv/bin/python -m app.evaluations.cli \
  --benchmark ../../data/evaluations/phase-4-benchmark.v1.json \
  --policy ../../data/evaluations/phase-4-gates.v1.json \
  --run ../../data/evaluations/runs/phase-4-planning-baseline.v1.json
```

The command writes a JSON report to standard output and exits with:

- `0`: every gate passed;
- `1`: at least one approved gate failed;
- `2`: no approved gate failed, but evidence or an owner approval is missing.

## Production evaluation procedure

1. Approve the production source registry and relevance labels. Replace proposed
   source slugs with the approved immutable slugs in a new benchmark version.
2. Approve and configure the evaluated model route under D-006, leaving provider
   response storage disabled.
3. Run all 45 cases against an isolated staging dataset. Store observations only;
   do not store provider-side response history or user data.
4. Set `resolved_blockers` only for prerequisites whose decision records and
   deployed configuration are verifiably complete.
5. Review unexpected retrievals for expired, unpublished, unsupported, or
   inapplicable knowledge. Any such result increments the eligibility-violation
   metric and fails the approved zero-violation gate.
6. Have Product + AI approve D-002 citation thresholds and AI + Platform approve
   D-006 retrieval, latency, and cost thresholds. Change only those gates from
   `proposed` to `approved` in a reviewed policy version.
7. Archive the run, report, prompt fingerprint, route registry version, source
   registry version, and deployment revision together as release evidence.

Never mark blocked metrics as waived or passing. A temporary exception requires
a separately approved release decision and does not change the evaluation result.
