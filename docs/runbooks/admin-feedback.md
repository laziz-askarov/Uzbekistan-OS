# Admin feedback operations

This runbook provisions the server-controlled feedback review roles and enables
the Supabase access-token hook. Customer-facing application code must never
write to `public.user_roles`.

## Deploy the database migration

Apply `202608120009_admin_feedback_rbac.sql` through the normal Supabase
migration workflow before publishing the web application. The migration:

- creates the `admin` and `reviewer` roles and their permissions;
- makes the role-permission mapping migration controlled;
- restricts role data from `anon` and `authenticated` users;
- adds the Custom Access Token Hook function;
- limits reviewers to feedback assigned to them;
- commits each feedback update and immutable audit entry in one transaction.

## Enable the access-token hook

In the Supabase dashboard, open **Authentication → Hooks**. Enable the
**Custom Access Token** hook and choose:

```text
public.custom_access_token_hook
```

The hook is executable by `supabase_auth_admin` only. Do not grant customers or
the application client access to it.

## Bootstrap staff roles

Use the Supabase SQL editor or another operator-only database connection. Find
the exact Auth user UUID first, then provision a role:

```sql
insert into public.user_roles (user_id, role, granted_by)
values ('AUTH_USER_UUID', 'admin', null)
on conflict (user_id) do update
set role = excluded.role, updated_at = now();
```

Use `reviewer` instead of `admin` for a reviewer. Role provisioning is an
operator action; there is intentionally no web route, form, or RPC available to
customer sessions for role changes.

After a role is added or changed, the staff member must sign out and sign back
in so Supabase issues an access token containing the new `user_role` claim.
Database authorization also checks the current `user_roles` row, so removing a
role blocks new database actions immediately even if an older token still
contains the claim.

## Operating the queue

Open `/admin/feedback` with a provisioned staff account.

- Admins see all feedback and can assign, update notes, resolve, dismiss, and
  reopen reports.
- Reviewers see only reports assigned to their own Auth user UUID. They can add
  notes and close active reports, but cannot assign or reopen them.
- Resolution and dismissal require internal notes.
- Each successful mutation records the actor, role, request ID, prior workflow
  state, new workflow state, action, and timestamp in `admin_audit_log`.

Do not place customer report details or assistant response text into audit
metadata or application logs. Those values remain in their source records.

## Revoke access

From an operator-only database connection:

```sql
delete from public.user_roles where user_id = 'AUTH_USER_UUID';
```

The user should also sign out. Verify `/admin/feedback` redirects the account
and that feedback RPC calls return `403`.
