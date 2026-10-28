# ADR 0026: Tourism-first brand and email trip inquiries

Status: Accepted 2026-10-28
Owner: Product (Laziz)
Supersedes in part: ADR 0014 priority order; design.md "internal visa workspace" framing

## Context

Uzbekistan OS launched as an account-gated visa planner across five domains.
The owner's commercial goal is trip inquiries for Kebab Travel, the Tashkent
travel company that operates the site, from travellers in the US and Europe,
and recognition by search and AI answer engines as the verified source on
Uzbekistan travel. The strategy is recorded in
`docs/strategy/brand-refresh-2026.md`.

## Decision

1. The public site is presented as "Uzbekistan OS by Kebab Travel". Tourism is
   the primary domain; immigration, everyday living, business registration and
   healthcare continue as the "Living in Uzbekistan" pillar.
2. Launch workflows (ADR 0014) remain approved, but arrival, visa eligibility,
   registration, extension and departure lead the content plan.
3. An email trip-inquiry form is in scope. It is a contact form: it stores an
   inquiry for staff to answer by email. Bookings, payments, appointments and
   government API integrations remain out of scope (AGENTS.md).
4. Editorial surfaces stay independent of the trip service. Kebab Travel
   appears in labelled service boxes, on `/trips`, on `/about`, and as the
   `Organization` in structured data. Guides carry no affiliate links.
5. The signed-in assistant and account signup keep working but are removed
   from public navigation until tourism knowledge is loaded.
6. The legacy Next.js visa pipeline (`lib/visa-ai.ts`, `lib/visa-workflows.ts`)
   is removed; the grounded FastAPI assistant is the only generation path. The
   extracted visa excerpts are kept as source material in
   `docs/visa-sources/visa-knowledge.extracted.json` for re-ingestion through
   the governed registry.

## Consequences

- New public pages: `/travel`, `/living`, `/trips`, `/about`, `/authors/[slug]`.
- New table `public.trip_inquiries` (service-role writes, staff reads via the
  admin client, no anon or authenticated access). Retention is 24 months after
  last handling; the privacy policy documents it (decision D-008 partially
  closed for this data class; account data retention remains open).
- Anti-abuse for the inquiry form: honeypot field, body limit, per-email daily
  limit. The Turnstile secret stays in Supabase Auth only (existing policy);
  server-side Turnstile verification for the form would need that policy
  revised.
- `tests/landing-page.test.mjs` now asserts the tourism-first framing; the
  visa-catalogue assertions are retired.
