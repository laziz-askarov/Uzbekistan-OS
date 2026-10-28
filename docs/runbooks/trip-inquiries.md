# Trip inquiries

Public visitors send trip-planning inquiries from `/trips`. Staff answer them
by email. Nothing is booked or paid on the site.

## Flow

1. `app/trips/inquiry-form.tsx` posts JSON to `POST /api/trips/inquiry`.
2. The route (`app/api/trips/inquiry/route.ts`) checks same-origin, JSON
   content type, an 8 KB body limit, the schema in `lib/trip-inquiry.ts`
   (including the empty honeypot field `website`), and a limit of five
   inquiries per email per 24 hours. It then inserts into
   `public.trip_inquiries` with the service-role client.
3. Staff with the `admin` or `reviewer` role read inquiries at
   `/admin/inquiries` (newest first, read-only) and reply from their mail
   client.

## Database

Migration: `supabase/migrations/202610280016_trip_inquiries.sql`. Row-level
security is enabled with no policies, and all privileges are revoked from
`anon` and `authenticated`, so only the service role can read or write.

Status values: `new`, `replied`, `closed`, `spam`. Update `status`,
`handled_by` and `handled_at` from the Supabase dashboard or SQL until an
admin action exists.

## Retention

Delete inquiries 24 months after `handled_at` (or `created_at` when never
handled), as stated in the privacy policy section "Trip inquiries". Until a
scheduled job exists, run quarterly:

```sql
delete from public.trip_inquiries
where coalesce(handled_at, created_at) < now() - interval '24 months';
```

## Logs

The route logs `trip_inquiry_started`, `trip_inquiry_rejected`,
`trip_inquiry_completed` and `trip_inquiry_failed` with the request ID,
outcome, travel month and traveller count only. Names, emails and messages
are never logged.
