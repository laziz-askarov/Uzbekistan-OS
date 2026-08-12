-- Server-controlled admin/reviewer roles and an auditable feedback workflow.
create type public.app_role as enum ('admin', 'reviewer');
comment on type public.app_role is
'Server-controlled staff roles. Add new values with a reviewed migration only.';

create type public.app_permission as enum (
  'feedback.read',
  'feedback.review',
  'feedback.assign',
  'feedback.reopen'
);

create table public.user_roles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role public.app_role not null,
  granted_by uuid references auth.users(id) on delete set null,
  granted_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.role_permissions (
  role public.app_role not null,
  permission public.app_permission not null,
  primary key (role, permission)
);

insert into public.role_permissions (role, permission) values
  ('reviewer', 'feedback.read'),
  ('reviewer', 'feedback.review'),
  ('admin', 'feedback.read'),
  ('admin', 'feedback.review'),
  ('admin', 'feedback.assign'),
  ('admin', 'feedback.reopen');

alter table public.guidance_feedback
  add column assigned_to uuid references auth.users(id) on delete set null;

create index guidance_feedback_assignee_status_created_idx
on public.guidance_feedback(assigned_to, status, created_at desc);

create table public.admin_audit_log (
  id bigint generated always as identity primary key,
  actor_id uuid not null,
  actor_role public.app_role not null,
  action text not null check (
    action in (
      'feedback.assigned',
      'feedback.updated',
      'feedback.resolved',
      'feedback.dismissed',
      'feedback.reopened'
    )
  ),
  entity_type text not null check (entity_type = 'guidance_feedback'),
  entity_id uuid not null,
  request_id text not null check (
    char_length(request_id) between 1 and 128
    and request_id ~ '^[a-zA-Z0-9._:-]+$'
  ),
  before_state jsonb not null,
  after_state jsonb not null,
  occurred_at timestamptz not null default now()
);

create index admin_audit_log_entity_occurred_idx
on public.admin_audit_log(entity_type, entity_id, occurred_at desc);

create index admin_audit_log_actor_occurred_idx
on public.admin_audit_log(actor_id, occurred_at desc);

alter table public.user_roles enable row level security;
alter table public.role_permissions enable row level security;
alter table public.admin_audit_log enable row level security;

revoke all privileges on public.user_roles from public, anon, authenticated;
revoke all privileges on public.role_permissions from public, anon, authenticated;
revoke all privileges on public.admin_audit_log from public, anon, authenticated;

create policy "auth_admin_reads_user_roles"
on public.user_roles for select
to supabase_auth_admin
using (true);

grant usage on schema public to supabase_auth_admin;
grant select on public.user_roles to supabase_auth_admin;

create or replace function public.prevent_role_permission_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'Role permissions are migration controlled';
end;
$$;

create trigger role_permissions_migration_controlled
before insert or update or delete on public.role_permissions
for each row execute function public.prevent_role_permission_mutation();

revoke all on function public.prevent_role_permission_mutation()
from public, anon, authenticated;

create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  claims jsonb := coalesce(event -> 'claims', '{}'::jsonb);
  assigned_role public.app_role;
begin
  select role
  into assigned_role
  from public.user_roles
  where user_id = (event ->> 'user_id')::uuid;

  if assigned_role is null then
    claims := claims - 'user_role';
  else
    claims := pg_catalog.jsonb_set(
      claims,
      '{user_role}',
      pg_catalog.to_jsonb(assigned_role)
    );
  end if;

  return pg_catalog.jsonb_set(event, '{claims}', claims);
end;
$$;

revoke all on function public.custom_access_token_hook(jsonb)
from public, anon, authenticated;
grant execute on function public.custom_access_token_hook(jsonb)
to supabase_auth_admin;

create or replace function public.authorize(requested_permission public.app_permission)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.user_roles assigned_role
    join public.role_permissions allowed_permission
      on allowed_permission.role = assigned_role.role
    where assigned_role.user_id = (select auth.uid())
      and assigned_role.role::text = (select auth.jwt() ->> 'user_role')
      and allowed_permission.permission = requested_permission
  );
$$;

revoke all on function public.authorize(public.app_permission)
from public, anon;
grant execute on function public.authorize(public.app_permission)
to authenticated;

create policy "guidance_feedback_staff_select"
on public.guidance_feedback for select
to authenticated
using (
  (select public.authorize('feedback.read'))
  and (
    (select auth.jwt() ->> 'user_role') = 'admin'
    or assigned_to = (select auth.uid())
  )
);

grant select on public.guidance_feedback to authenticated;

create policy "admin_audit_staff_select"
on public.admin_audit_log for select
to authenticated
using (
  (select public.authorize('feedback.read'))
  and (
    (select auth.jwt() ->> 'user_role') = 'admin'
    or actor_id = (select auth.uid())
  )
);

grant select on public.admin_audit_log to authenticated;

create or replace function public.prevent_admin_audit_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'Admin audit records are immutable';
end;
$$;

create trigger admin_audit_log_immutable
before update or delete on public.admin_audit_log
for each row execute function public.prevent_admin_audit_mutation();

revoke all on function public.prevent_admin_audit_mutation()
from public, anon, authenticated;

create or replace function public.update_guidance_feedback(
  p_feedback_id uuid,
  p_next_status text,
  p_next_admin_notes text,
  p_next_assigned_to uuid,
  p_request_id text
)
returns public.guidance_feedback
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor_user_id uuid := (select auth.uid());
  actor_user_role public.app_role;
  before_record public.guidance_feedback;
  after_record public.guidance_feedback;
  target_role public.app_role;
  audit_action text;
begin
  if actor_user_id is not null then
    select role
    into actor_user_role
    from public.user_roles
    where user_id = actor_user_id
      and role::text = (select auth.jwt() ->> 'user_role');
  end if;

  if actor_user_role is null or not (select public.authorize('feedback.review')) then
    raise insufficient_privilege using message = 'Feedback review permission required';
  end if;

  if p_next_status not in ('new', 'reviewing', 'resolved', 'dismissed') then
    raise invalid_parameter_value using message = 'Unsupported feedback status';
  end if;
  if p_next_admin_notes is not null
    and char_length(p_next_admin_notes) > 4000 then
    raise invalid_parameter_value using message = 'Admin notes are too long';
  end if;
  if p_request_id is null
    or char_length(p_request_id) not between 1 and 128
    or p_request_id !~ '^[a-zA-Z0-9._:-]+$' then
    raise invalid_parameter_value using message = 'Invalid request id';
  end if;

  select *
  into before_record
  from public.guidance_feedback
  where id = p_feedback_id
  for update;
  if before_record.id is null then
    raise no_data_found using message = 'Feedback not found';
  end if;

  if actor_user_role = 'reviewer' then
    if before_record.assigned_to is distinct from actor_user_id
      or p_next_assigned_to is distinct from actor_user_id
      or before_record.status in ('resolved', 'dismissed') then
      raise insufficient_privilege using message = 'Reviewer assignment does not permit this change';
    end if;
  elsif actor_user_role = 'admin' then
    if p_next_assigned_to is not null then
      select role into target_role
      from public.user_roles
      where user_id = p_next_assigned_to;
      if target_role is null then
        raise invalid_parameter_value using message = 'Assignee must have a staff role';
      end if;
    end if;
  else
    raise insufficient_privilege using message = 'Staff role required';
  end if;

  if before_record.status in ('resolved', 'dismissed')
    and p_next_status in ('new', 'reviewing')
    and not (select public.authorize('feedback.reopen')) then
    raise insufficient_privilege using message = 'Reopen permission required';
  end if;

  if p_next_status in ('resolved', 'dismissed') then
    if nullif(pg_catalog.btrim(coalesce(p_next_admin_notes, '')), '') is null then
      raise invalid_parameter_value using message = 'Resolution notes are required';
    end if;
  end if;

  update public.guidance_feedback
  set
    status = p_next_status,
    admin_notes = nullif(pg_catalog.btrim(p_next_admin_notes), ''),
    assigned_to = p_next_assigned_to,
    reviewed_by = case
      when p_next_status in ('resolved', 'dismissed')
        and before_record.status is distinct from p_next_status then actor_user_id
      when p_next_status in ('resolved', 'dismissed') then before_record.reviewed_by
      else null
    end,
    reviewed_at = case
      when p_next_status in ('resolved', 'dismissed')
        and before_record.status is distinct from p_next_status then statement_timestamp()
      when p_next_status in ('resolved', 'dismissed') then before_record.reviewed_at
      else null
    end,
    updated_at = statement_timestamp()
  where id = p_feedback_id
  returning * into after_record;

  audit_action := case
    when before_record.status in ('resolved', 'dismissed')
      and after_record.status in ('new', 'reviewing') then 'feedback.reopened'
    when before_record.status is distinct from after_record.status
      and after_record.status = 'resolved' then 'feedback.resolved'
    when before_record.status is distinct from after_record.status
      and after_record.status = 'dismissed' then 'feedback.dismissed'
    when before_record.assigned_to is distinct from after_record.assigned_to then 'feedback.assigned'
    else 'feedback.updated'
  end;

  insert into public.admin_audit_log (
    actor_id,
    actor_role,
    action,
    entity_type,
    entity_id,
    request_id,
    before_state,
    after_state
  ) values (
    actor_user_id,
    actor_user_role,
    audit_action,
    'guidance_feedback',
    p_feedback_id,
    p_request_id,
    pg_catalog.jsonb_build_object(
      'status', before_record.status,
      'admin_notes_present', before_record.admin_notes is not null,
      'assigned_to', before_record.assigned_to,
      'reviewed_by', before_record.reviewed_by,
      'reviewed_at', before_record.reviewed_at,
      'updated_at', before_record.updated_at
    ),
    pg_catalog.jsonb_build_object(
      'status', after_record.status,
      'admin_notes_present', after_record.admin_notes is not null,
      'admin_notes_changed', before_record.admin_notes is distinct from after_record.admin_notes,
      'assigned_to', after_record.assigned_to,
      'reviewed_by', after_record.reviewed_by,
      'reviewed_at', after_record.reviewed_at,
      'updated_at', after_record.updated_at
    )
  );

  return after_record;
end;
$$;

revoke all on function public.update_guidance_feedback(uuid, text, text, uuid, text)
from public, anon;
grant execute on function public.update_guidance_feedback(uuid, text, text, uuid, text)
to authenticated;

comment on table public.user_roles is
'Server-controlled staff roles. No customer-facing role mutation API exists.';
comment on table public.admin_audit_log is
'Immutable audit trail for staff changes to customer guidance reports.';
