# ADR 0023: Progressive Supabase customer identity

- Status: Accepted
- Date: 2026-08-10
- Resolves: D-003 for customer-facing authentication

## Context

Uzbekistan OS must remain immediately useful to visitors while providing durable, access-controlled customer workspaces. Requiring an account before a public-information question would add friction without adding proportional security. Treating every signed-in customer as government-verified would overstate trust and encourage unnecessary collection of sensitive identifiers.

## Decision

- Use Supabase Auth and PostgreSQL RLS for customer identity and workspace ownership.
- Keep general questions available without an upfront account screen. Create a Supabase anonymous user only when a visitor first needs persisted conversation state.
- Make passwordless email links the primary account creation and sign-in method. A new customer upgrades the existing anonymous identity so its owned rows retain the same user ID. This replaces phone-first signup for the initial launch while avoiding SMS cost and ensuring foreign visitors can register without a local SIM.
- Retain the signed Send SMS HTTP Hook and Eskiz-backed provider adapter as dormant infrastructure for a later approved phone verification option. Do not expose phone signup in the launch UI.
- Permit Google and Apple as secondary identity providers after their provider credentials and redirect URLs are configured. Do not add password authentication to the MVP.
- Represent progressive trust with identity levels: `0` anonymous, `1` account, `2` verified contact method, and `3` OneID verified.
- Keep trust fields server-controlled. Customers may update ordinary profile fields but cannot update their email, phone, identity level, or OneID verification fields through RLS-protected client access.
- Do not collect PINFL, passport numbers, or other government identifiers during ordinary account creation.
- Defer OneID/Mobile-ID, passkeys, uploads, reminders, and direct government integrations to separately approved scope and security reviews.
- Use secure cookie-backed Supabase sessions in the Next.js application. Server authorization verifies the user or claims and never trusts unverified client session data.

## Consequences

- Guest conversations can be isolated with the same `auth.uid()` ownership model used for permanent accounts.
- Returning customers sign in to their existing account; automatic merging between an unrelated guest identity and an existing account is not part of this slice.
- Production email authentication depends on approved redirect URLs, deliverable templates, rate limits, and CAPTCHA/abuse protection. Phone verification remains dependent on the separately funded and configured Eskiz/DevSMS route if it is re-enabled later.
- The provider-neutral FastAPI principal boundary remains valid. Connecting Supabase JWT subjects to internal administrative roles requires a separate fail-closed verifier configuration and does not grant customer accounts administrative access.
- Anonymous-user retention and deletion must be finalized under D-008 before alpha.
