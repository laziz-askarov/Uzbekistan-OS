# ADR 0011: Safe text-first PDF ingestion

- Status: Accepted for the PDF ingestion slice
- Date: 2026-08-01

## Context

Some approved official sources publish procedural guidance as PDFs. PDF parsing expands the ingestion attack surface and can silently produce unusable evidence when a file is encrypted, scanned without a text layer, mislabeled, malformed, or excessively large. Reviewers also need stable page boundaries so extracted text can be compared with its source evidence.

## Decision

- A registry entry must explicitly declare `source_type: pdf`; its response must use the exact `application/pdf` media type. PDF responses for any other registered source type fail closed.
- Require a `%PDF-` signature within the first 1,024 response bytes before invoking the parser.
- Use the pinned `pypdf` adapter in strict mode and reject encrypted or malformed documents as terminal ingestion failures.
- Limit a PDF to 250 pages and all normalized source content to 2,000,000 characters by default. Both limits are environment-configurable, while the existing response-byte cap remains the first guard.
- Extract text page by page and preserve each non-empty page as a `Page N` artifact section. Page numbers reflect the physical PDF page order, including skipped image-only pages.
- Reject documents with no extractable text. OCR is not enabled because OCR is outside the MVP boundary and would require separate quality, language, security, and review controls.
- Store the original response and the canonical extraction artifact through the existing content-addressed evidence boundary. PDF approval does not bypass review or publication controls.
- Keep production source authorization separate from parser support. This decision approves an adapter boundary, not a real source.

## Consequences

- Text-based official PDFs can enter the same snapshot, extraction, review, and audit pipeline as HTML sources while retaining page-level provenance.
- Password-protected, scanned, or malformed files require an owner-approved source alternative; operators must not manually extract or publish their contents.
- Complex reading order, tables, and multi-column layouts can still be imperfect and must be checked in the reviewer console before publication.
- Raising page, character, or byte limits increases parsing cost and must be reviewed as a capacity and security change.
- Source-specific PDF adapters, production-source approval, OCR, and layout-aware table extraction remain future work.
