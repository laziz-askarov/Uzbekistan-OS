# ADR 0023: Progressive Supabase customer identity

- Status: Accepted
- Date: 2026-08-10
- Resolves: D-003 for customer-facing authentication

## Context

Uzbekistan OS must remain immediately useful to visitors while providing durable, access-controlled customer workspaces. Requiring an account before a public-information question would add friction without adding proportional security. Treating every signed-in customer as government-verified would overstate trust and encourage unnecessary collection of sensitive identifiers.

## Decision

- Use Supabase Auth and PostgreSQL RLS for customer identity and workspace ownership.
- Keep general questions available without an upfront account screen. Create a Supabase anonymous user only when a visitor first needs persisted conversation state.
- Make phone OTP the primary account creation and sign-in method, with `+998` as the local convenience default rather than an eligibility restriction. Accept valid international E.164 numbers so foreign visitors can register before obtaining a local SIM. A new customer upgrades the existing anonymous identity so its owned rows retain the same user ID.
- Deliver launch OTP messages through Supabase's signed Send SMS HTTP Hook and an Eskiz-backed local route. Keep the provider behind a server-only adapter so another approved Uzbekistan route can replace or back it up without changing identity logic.
- Permit Google and Apple as secondary identity providers after their provider credentials and redirect URLs are configured. Do not add password authentication to the MVP.
- Represent progressive trust with identity levels: `0` anonymous, `1` account, `2` phone verified, and `3` OneID verified.
- Keep trust fields server-controlled. Customers may update ordinary profile fields but cannot update their phone, identity level, or OneID verification fields through RLS-protected client access.
- Do not collect PINFL, passport numbers, or other government identifiers during ordinary account creation.
- Defer OneID/Mobile-ID, passkeys, uploads, reminders, and direct government integrations to separately approved scope and security reviews.
- Use secure cookie-backed Supabase sessions in the Next.js application. Server authorization verifies the user or claims and never trusts unverified client session data.

## Consequences

- Guest conversations can be isolated with the same `auth.uid()` ownership model used for permanent accounts.
- Returning customers sign in to their existing account; automatic merging between an unrelated guest identity and an existing account is not part of this slice.
- Production phone authentication depends on a funded Eskiz/DevSMS account, registered or pre-approved OTP template, rate limits, CAPTCHA/abuse protection, and the signed hook configuration in Supabase. Provider prices are operational inputs and are not hard-coded as guarantees.
- The provider-neutral FastAPI principal boundary remains valid. Connecting Supabase JWT subjects to internal administrative roles requires a separate fail-closed verifier configuration and does not grant customer accounts administrative access.
- Anonymous-user retention and deletion must be finalized under D-008 before alpha.
