# Source registry

`registry.development.json` is deliberately non-production. It proves the registry contract without implying that an external source has been approved, that crawling is legally permitted, or that a launch workflow has been selected.

A source may be fetched automatically only when all of the following are true:

- `status` is `approved`;
- `crawl_policy` is `allowed`;
- `production_eligible` is `true`;
- an accountable `owner` and `reviewed_at` timestamp are present.

Adding a production source requires source ownership, crawl-permission, workflow, precedence, and freshness decisions. Validate registry changes with `python scripts/validate_contracts.py` from the repository root.
