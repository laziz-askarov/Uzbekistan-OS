# Retrieval operations runbook

## Current boundary

The Phase 4 retrieval core is internal. It does not expose `/knowledge/search`
or chat generation. Query planning is deterministic, hybrid retrieval reads only
`knowledge.retrievable_chunks`, and evidence packing retains reviewed citation
identifiers and locators.

Both lexical and vector SQL additionally reject a document version if any linked
source or organization is inactive, unofficial, blocked, or pending review. This
protects retrieval when source support is revoked after publication without
waiting for vectors to be deleted.

## Failure and insufficiency behavior

- Invalid control delimiters fail before retrieval.
- A semantic request requires a finite query vector and configured model key.
- Language, domain, trust, and supplied applicability mismatches are excluded.
- Conflicting candidate lineage is an integrity error.
- Uncited chunks never enter evidence packs.
- Duplicate content hashes enter once.
- Retrieved instruction-override patterns are quarantined rather than supplied
  to later orchestration.
- No remaining evidence produces `status: insufficient`; callers must not ask a
  model to answer from general knowledge.

## Validation

From the repository root:

```bash
apps/api/.venv/bin/python -m ruff check apps/api
apps/api/.venv/bin/python -m pytest apps/api/tests/test_retrieval_planning.py apps/api/tests/test_retrieval.py apps/api/tests/test_retrieval_repositories.py
```

The planning fixture in `data/evaluations/retrieval-planning.v1.json` covers all
15 launch flows across English, Uzbek, and Russian. It is a routing benchmark,
not a retrieval-quality benchmark. Expected official sources, relevance grades,
abstention cases, latency, and cost thresholds require approved content and the
D-006 embedding decision.
