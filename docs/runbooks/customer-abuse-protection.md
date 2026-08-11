# Customer abuse protection

Uzbekistan OS uses layered controls rather than relying on one provider:

- Cloudflare Turnstile challenges account creation, password sign-in, and
  password recovery. Supabase Auth validates each challenge token server-side.
- Supabase Auth applies provider-level email, SMS, OTP, verification, and
  session rate limits.
- PostgreSQL applies durable per-account limits to application actions before
  expensive or write-heavy work begins.

## Enable Turnstile

1. Create a managed Cloudflare Turnstile widget. Add the production hostname
   `www.uzbekistanos.com`, the apex hostname, and the stable staging hostname.
   Add `localhost` only to the development widget.
2. Add the widget's public site key to the appropriate Vercel environment as
   `NEXT_PUBLIC_TURNSTILE_SITE_KEY`.
3. In Supabase Dashboard, open **Authentication → Bot and Abuse Protection**,
   choose Cloudflare Turnstile, enter the Turnstile secret key, and enable
   CAPTCHA.
4. Exercise email signup, email sign-in, phone signup, phone sign-in, and email
   password recovery in staging before repeating the configuration in
   production.

The Turnstile secret belongs only in Supabase. Do not put it in Vercel, a local
environment file, browser code, logs, or Git. The application omits the widget
when the public site key is absent, so enable Supabase CAPTCHA only after the
matching public key has been deployed to that environment.

References: [Supabase CAPTCHA](https://supabase.com/docs/guides/auth/auth-captcha),
[Cloudflare server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

## Rate-limit policy

| Action | Limit | Enforcement |
| --- | ---: | --- |
| Chat | 20 per 10 minutes and 100 per day | PostgreSQL, per account |
| Guidance feedback | 10 per hour | PostgreSQL, per account |
| Account export | 3 per hour | PostgreSQL, per account |
| Auth and OTP operations | Supabase project and IP limits | Supabase Auth |

Application routes return HTTP `429`, `Retry-After`, and
`X-RateLimit-Remaining` when a durable quota is exhausted. Quota RPC failures
fail closed with HTTP `503`; they do not allow unmetered work.

Review the Supabase Auth limits in **Authentication → Rate Limits** after every
provider or traffic change. Keep resend intervals enabled and watch legitimate
failure rates before tightening project-wide email or SMS caps. Supabase's
current controls and defaults are documented in
[Auth rate limits](https://supabase.com/docs/guides/auth/rate-limits).

Do not use a public client IP header as an identity key without a reviewed
trusted-proxy boundary. Per-account database quotas remain authoritative for
authenticated application actions.
