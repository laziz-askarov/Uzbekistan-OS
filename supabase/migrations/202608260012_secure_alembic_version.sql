-- Keep the API migration ledger inaccessible through Supabase's exposed Data API.
-- Alembic connects directly as the postgres table owner and does not require
-- anon, authenticated, or service-role access to this table.
alter table public.alembic_version enable row level security;

revoke all privileges on table public.alembic_version
from public, anon, authenticated, service_role;

comment on table public.alembic_version is
'Private Alembic migration ledger. Client roles must not access this table.';
