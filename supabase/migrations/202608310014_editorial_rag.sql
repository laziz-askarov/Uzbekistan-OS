-- Opt-in editorial content retrieval for reviewed, published blog revisions.
--
-- This is the Supabase SQL Editor companion to API Alembic revision
-- 20260831_0011. Run the whole file as one query.

begin;

do $$
declare
  current_revision text;
begin
  if to_regclass('public.alembic_version') is null then
    raise exception
      'Missing public.alembic_version. Apply API migrations through 20260831_0010 first.';
  end if;

  select version_num into current_revision
  from public.alembic_version
  limit 1;

  if current_revision = '20260831_0011' then
    raise exception 'Editorial RAG migration 20260831_0011 is already applied.';
  end if;

  if current_revision is distinct from '20260831_0010' then
    raise exception
      'Expected Alembic revision 20260831_0010, found %.',
      coalesce(current_revision, '<none>');
  end if;

  if to_regclass('content.rag_chunks') is not null then
    raise exception
      'content.rag_chunks already exists while the migration ledger is at 20260831_0010. Review the database before retrying.';
  end if;
end;
$$;

alter table content.post_versions
  add column include_in_rag boolean default false not null;

create table content.rag_chunks (
  post_version_id uuid not null,
  section_id varchar(160) not null,
  ordinal integer not null,
  heading varchar(500) not null,
  content text not null,
  content_hash varchar(64) not null,
  token_count integer not null,
  id uuid default gen_random_uuid() not null,
  created_at timestamptz default now() not null,
  constraint pk_rag_chunks primary key (id),
  constraint ck_rag_chunks_ordinal_nonnegative check (ordinal >= 0),
  constraint ck_rag_chunks_token_count_positive check (token_count > 0),
  constraint fk_rag_chunks_post_version_id_post_versions
    foreign key (post_version_id)
    references content.post_versions (id) on delete cascade,
  constraint uq_content_rag_chunk_ordinal unique (post_version_id, ordinal)
);

create index ix_content_rag_chunks_post_version_id
  on content.rag_chunks (post_version_id);

create or replace function content.guard_post_version_rag_update()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.status <> 'draft'
     and new.include_in_rag is distinct from old.include_in_rag then
    raise exception 'non-draft RAG eligibility cannot be edited';
  end if;
  return new;
end;
$$;

create trigger trg_content_post_versions_rag_guard
before update on content.post_versions
for each row execute function content.guard_post_version_rag_update();

alter table content.rag_chunks enable row level security;
revoke all privileges on table content.rag_chunks from public;

do $$
declare
  role_name text;
begin
  foreach role_name in array array['anon', 'authenticated', 'service_role']
  loop
    if exists (select 1 from pg_roles where rolname = role_name) then
      execute format(
        'revoke all privileges on table content.rag_chunks from %I',
        role_name
      );
    end if;
  end loop;
end;
$$;

update public.alembic_version
set version_num = '20260831_0011'
where version_num = '20260831_0010';

do $$
begin
  if not exists (
    select 1 from public.alembic_version
    where version_num = '20260831_0011'
  ) then
    raise exception 'Failed to advance the Alembic migration ledger.';
  end if;
end;
$$;

commit;
