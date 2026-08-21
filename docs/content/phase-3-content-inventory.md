# Phase 3 production content inventory

Status: **initial Uzbek sources approved; document publication review required**
Prepared: 2026-08-01

This inventory defines the first 21 language-specific document candidates for the
Arrival & Entry Assistant and Visa Eligibility Checker. It is deliberately not a
publication manifest. No candidate may move to the review queue until its source,
crawl policy, freshness owner, adapter behavior, and language-specific evidence
have been approved.

## Candidate set

| # | Document slug | Workflow | Risk | Language | Primary evidence | Status |
| -: | --- | --- | --- | --- | --- | --- |
| 1 | `arrival-overview-en` | Arrival & Entry | Lower | EN | Tourism guideline + MFA visa page | Source approval pending |
| 2 | `arrival-overview-uz` | Arrival & Entry | Lower | UZ | MFA Uzbek page; translation evidence required | Source approval pending |
| 3 | `arrival-overview-ru` | Arrival & Entry | Lower | RU | MFA Russian page; translation evidence required | Source approval pending |
| 4 | `passport-entry-documents-en` | Arrival & Entry | Higher | EN | MFA visa page | Source approval pending |
| 5 | `passport-entry-documents-uz` | Arrival & Entry | Higher | UZ | MFA Uzbek page | Source approval pending |
| 6 | `passport-entry-documents-ru` | Arrival & Entry | Higher | RU | MFA Russian page | Source approval pending |
| 7 | `visitor-registration-en` | Arrival & Entry | Higher | EN | Tourism guideline; legal authority cross-check required | Source approval pending |
| 8 | `visitor-registration-uz` | Arrival & Entry | Higher | UZ | Language-specific official evidence required | Evidence gap |
| 9 | `visitor-registration-ru` | Arrival & Entry | Higher | RU | Language-specific official evidence required | Evidence gap |
| 10 | `customs-and-restricted-goods-en` | Arrival & Entry | Higher | EN | Tourism guideline; Customs Committee cross-check required | Evidence gap |
| 11 | `customs-and-restricted-goods-uz` | Arrival & Entry | Higher | UZ | Customs Committee language-specific evidence required | Evidence gap |
| 12 | `customs-and-restricted-goods-ru` | Arrival & Entry | Higher | RU | Customs Committee language-specific evidence required | Evidence gap |
| 13 | `currency-declaration-en` | Arrival & Entry | Higher | EN | Tourism guideline; Central Bank/Customs cross-check required | Evidence gap |
| 14 | `currency-declaration-uz` | Arrival & Entry | Higher | UZ | Language-specific official evidence required | Evidence gap |
| 15 | `currency-declaration-ru` | Arrival & Entry | Higher | RU | Language-specific official evidence required | Evidence gap |
| 16 | `visa-eligibility-en` | Visa Eligibility | Higher | EN | MFA visa page | Source approval pending |
| 17 | `visa-eligibility-uz` | Visa Eligibility | Higher | UZ | MFA Uzbek page | Source approval pending |
| 18 | `visa-eligibility-ru` | Visa Eligibility | Higher | RU | MFA Russian page | Source approval pending |
| 19 | `evisa-application-en` | Visa Eligibility | Higher | EN | Official e-Visa portal | Adapter and source approval pending |
| 20 | `evisa-application-uz` | Visa Eligibility | Higher | UZ | Official e-Visa portal | Adapter and source approval pending |
| 21 | `evisa-application-ru` | Visa Eligibility | Higher | RU | Official e-Visa portal | Adapter and source approval pending |

The label “Lower” is a content-review classification, not the database domain
risk level. The seeded `tourism` domain is currently `medium`; Phase 3 cannot
claim a database-enforced low-risk workflow unless product/domain owners either
approve a low-risk domain classification or revise the acceptance wording.

## Proposed official sources

The historical proposal is stored in
`data/sources/registry.production.proposed.json`. The approved runtime set is in
`registry.staging.json` and `registry.production.json`.

- Ministry of Foreign Affairs visa guidance in Uzbek, using the
  `govuz-activity-html` adapter.
- Ministry of Foreign Affairs official e-Visa Uzbek localization payload, using
  the `evisa-uz-localization-json` adapter.
- English, Russian, and Tourism Committee candidates remain non-production until
  separately approved under ADR 0025.

## Approval checklist

For each source, the accountable content owner must record:

1. authority and precedence for each claim class;
2. permission for automated crawl or an explicit `manual_only` decision;
3. a tested adapter and expected canonical URL behavior;
4. freshness interval, expiry policy, and incident owner;
5. supported language evidence and human translation reviewer;
6. a completed high-risk legal/domain review before publication.

Only after those checks may an operator copy approved entries into the deployed
environment registry, set ownership/review timestamps, and mark them production
eligible.
