# ADR 0023: Progressive Supabase customer identity

- Status: Accepted
- Date: 2026-08-10
- Resolves: D-003 for customer-facing authentication

## Context

Uzbekistan OS provides durable, access-controlled customer workspaces. Public visa information remains visible on the landing page, while the interactive assistant requires an account so conversations are never stored under an anonymous identity. Treating every signed-in customer as government-verified would still overstate trust and encourage unnecessary collection of sensitive identifiers.

## Decision

- Use Supabase Auth and PostgreSQL RLS for customer identity and workspace ownership.
- Require a verified customer account before entering the interactive assistant or calling its generation API. Do not create anonymous Supabase users in the application.
- Make email plus password the primary account creation and sign-in method. Require email confirmation after registration.
- Offer international phone plus password as the secondary account method, with SMS OTP required to confirm a new phone registration. Keep the signed Send SMS HTTP Hook and DevSMS provider adapter behind the Supabase provider boundary.
- Permit Google and Apple as secondary identity providers after their provider credentials and redirect URLs are configured.
- Represent progressive trust with identity levels: `0` anonymous, `1` account, `2` verified contact method, and `3` OneID verified.
- Keep trust fields server-controlled. Customers may update ordinary profile fields but cannot update their email, phone, identity level, or OneID verification fields through RLS-protected client access.
- Do not collect PINFL, passport numbers, or other government identifiers during ordinary account creation.
- Defer OneID/Mobile-ID, passkeys, uploads, reminders, and direct government integrations to separately approved scope and security reviews.
- Use secure cookie-backed Supabase sessions in the Next.js application. Server authorization verifies the user or claims and never trusts unverified client session data.

## Consequences

- Every saved conversation is owned by a verified email or phone account under the same `auth.uid()` RLS boundary.
- Returning customers sign in to their existing account. Anonymous-to-account merging is not part of this slice.
- Production email authentication depends on approved redirect URLs, deliverable templates, rate limits, and CAPTCHA/abuse protection. Phone verification depends on the configured DevSMS route and SMS abuse controls.
- The provider-neutral FastAPI principal boundary remains valid. Connecting Supabase JWT subjects to internal administrative roles requires a separate fail-closed verifier configuration and does not grant customer accounts administrative access.
- Existing anonymous records, if any, require an explicit retention or deletion decision under D-008 before alpha.
