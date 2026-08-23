# ADR 0025: Uzbek canonical sources and freshness

- Status: Accepted
- Date: 2026-08-21
- Owner: Laziz (`laziz@cogotulsa.com`)

## Context

The first grounded workflows need a small, reviewable official evidence set. The
source proposal included English, Uzbek, and Russian pages, but publishing each
language as though it were equivalent would create unreviewed translation and
precedence risk. Procedural information also becomes unsafe when it remains
retrievable after its review window.

## Decision

The initial production registry contains only the official Uzbek MFA visa page
and the official Uzbek e-visa localization payload. Both remain
`manual_only` until automated crawl permission and change behavior are reviewed.
The Uzbek source text is canonical. English or Russian output may be introduced
only through a separately reviewed translation publication linked to its Uzbek
version; model-generated translation alone is not publication evidence.

Publication review windows are:

- 30 calendar days for immigration, business registration, and healthcare;
- 60 calendar days for everyday living;
- 180 calendar days for tourism-only guidance.

When a document covers multiple domains, the shortest window applies. A version
past `effective_until` is not eligible for retrieval. Reviewers may expire a
version earlier whenever the official source changes or its authority becomes
uncertain. A replacement must retain the source snapshot, extraction artifact,
review decision, and publication audit lineage.

## Consequences

The assistant initially answers only where published Uzbek evidence matches the
query and applicability context. Missing language-specific evidence produces a
safe insufficiency response. The admin publication workflow must include an
`effective_until` date that respects the applicable review window before launch
content is marked ready.

## Changed artifacts

- `data/sources/registry.staging.json`
- `data/sources/registry.production.json`
- `data/sources/registry.production.proposed.json`
- `docs/content/phase-3-content-inventory.md`
- source-specific ingestion adapter tests
