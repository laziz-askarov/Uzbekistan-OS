# Source registry

`registry.development.json` is deliberately non-production. It proves the registry contract without implying that an external source has been approved, that crawling is legally permitted, or that a launch workflow has been selected.

A source may be fetched automatically only when all of the following are true:

- `status` is `approved`;
- `crawl_policy` is `allowed`;
- `production_eligible` is `true`;
- an accountable `owner` and `reviewed_at` timestamp are present.

Registry version 1.1 also requires an ISO 3166-1 alpha-2 `country_iso2` for each organization. Adding a non-null `schedule` opts an otherwise eligible source into automatic crawl slots and requires an approved `interval_minutes` and bounded `max_attempts`. A null schedule leaves the source available only to explicit operational enqueue.

`APP_ENV` must exactly match the registry's `environment`. Synchronization upserts stable organization/source UUIDs and marks rows absent from that environment's registry inactive; it never deletes historical lineage. Run it with:

```bash
apps/api/.venv/bin/python -m app.worker sync-registry
```

Adding a production source requires source ownership, crawl permission, workflow, precedence, and freshness decisions. Validate registry changes with `apps/api/.venv/bin/python scripts/validate_contracts.py` from the repository root.
