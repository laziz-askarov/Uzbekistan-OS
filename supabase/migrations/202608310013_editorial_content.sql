-- Secure, versioned editorial content foundation.
--
-- This is the Supabase SQL Editor companion to API Alembic revision
-- 20260831_0010. Run the whole file as one query. The transaction and
-- preflight checks make a wrong-order or repeated execution fail safely.

begin;

do $$
declare
  current_revision text;
begin
  if to_regclass('public.alembic_version') is null then
    raise exception
      'Missing public.alembic_version. Apply API migrations through 20260825_0009 first.';
  end if;

  select version_num into current_revision
  from public.alembic_version
  limit 1;

  if current_revision = '20260831_0010' then
    raise exception 'Editorial content migration 20260831_0010 is already applied.';
  end if;

  if current_revision is distinct from '20260825_0009' then
    raise exception
      'Expected Alembic revision 20260825_0009, found %.',
      coalesce(current_revision, '<none>');
  end if;

  if to_regclass('content.posts') is not null then
    raise exception
      'content.posts already exists while the migration ledger is at 20260825_0009. Review the database before retrying.';
  end if;
end;
$$;

insert into identity.roles (id, key, name, description)
values (
  '00000000-0000-0000-0000-000000004004',
  'content_author',
  'Content author',
  'May create and revise editorial content drafts.'
);

create schema if not exists content;

create table content.authors (
  principal_id uuid,
  slug citext not null,
  name varchar(240) not null,
  bio text,
  avatar_url text,
  profile_url text,
  is_active boolean default true not null,
  id uuid default gen_random_uuid() not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null,
  constraint pk_authors primary key (id),
  constraint fk_authors_principal_id_principals
    foreign key (principal_id) references identity.principals (id) on delete set null,
  constraint uq_authors_principal_id unique (principal_id),
  constraint uq_authors_slug unique (slug)
);

create table content.posts (
  slug citext not null,
  content_type varchar(24) not null,
  domain_id uuid,
  language_id uuid not null,
  translation_group_id uuid default gen_random_uuid() not null,
  status varchar(20) default 'draft' not null,
  created_by_principal_id uuid not null,
  id uuid default gen_random_uuid() not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null,
  constraint pk_posts primary key (id),
  constraint ck_posts_content_type_allowed
    check (content_type in ('article', 'guide', 'platform_update', 'interview')),
  constraint ck_posts_status_allowed
    check (status in ('draft', 'in_review', 'approved', 'published', 'stale', 'archived')),
  constraint fk_posts_domain_id_domains
    foreign key (domain_id) references knowledge.domains (id) on delete restrict,
  constraint fk_posts_language_id_languages
    foreign key (language_id) references geography.languages (id) on delete restrict,
  constraint fk_posts_created_by_principal_id_principals
    foreign key (created_by_principal_id)
    references identity.principals (id) on delete restrict,
  constraint uq_posts_slug unique (slug)
);

create index ix_content_posts_domain_id on content.posts (domain_id);
create index ix_content_posts_language_id on content.posts (language_id);
create index ix_content_posts_translation_group_id
  on content.posts (translation_group_id);
create index ix_content_posts_created_by_principal_id
  on content.posts (created_by_principal_id);
create index ix_content_posts_status_domain
  on content.posts (status, domain_id);

create table content.post_versions (
  post_id uuid not null,
  version_number integer not null,
  title varchar(500) not null,
  summary text not null,
  body_markdown text not null,
  structured_content jsonb default '{}'::jsonb not null,
  seo_title varchar(70),
  seo_description varchar(200),
  canonical_url text,
  hero_image_url text,
  hero_image_alt varchar(500),
  author_id uuid not null,
  status varchar(20) default 'draft' not null,
  checksum_sha256 varchar(64) not null,
  created_by_principal_id uuid not null,
  submitted_at timestamptz,
  reviewed_by_principal_id uuid,
  reviewed_at timestamptz,
  decision_reason text,
  published_by_principal_id uuid,
  published_at timestamptz,
  review_due_at timestamptz,
  id uuid default gen_random_uuid() not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null,
  constraint pk_post_versions primary key (id),
  constraint ck_post_versions_version_number_positive
    check (version_number >= 1),
  constraint ck_post_versions_status_allowed
    check (status in ('draft', 'in_review', 'approved', 'published', 'stale', 'archived')),
  constraint ck_post_versions_submission_fields_consistent
    check (status = 'draft' or submitted_at is not null),
  constraint ck_post_versions_review_fields_consistent
    check (
      status not in ('approved', 'published', 'stale', 'archived')
      or (reviewed_by_principal_id is not null and reviewed_at is not null)
    ),
  constraint ck_post_versions_publication_fields_consistent
    check (
      status not in ('published', 'stale', 'archived')
      or (published_by_principal_id is not null and published_at is not null)
    ),
  constraint fk_post_versions_post_id_posts
    foreign key (post_id) references content.posts (id) on delete cascade,
  constraint fk_post_versions_author_id_authors
    foreign key (author_id) references content.authors (id) on delete restrict,
  constraint fk_post_versions_created_by_principal_id_principals
    foreign key (created_by_principal_id)
    references identity.principals (id) on delete restrict,
  constraint fk_post_versions_reviewed_by_principal_id_principals
    foreign key (reviewed_by_principal_id)
    references identity.principals (id) on delete restrict,
  constraint fk_post_versions_published_by_principal_id_principals
    foreign key (published_by_principal_id)
    references identity.principals (id) on delete restrict,
  constraint uq_content_post_version_number unique (post_id, version_number)
);

create index ix_content_post_versions_post_id
  on content.post_versions (post_id);
create index ix_content_post_versions_author_id
  on content.post_versions (author_id);
create index ix_content_post_versions_status_review_due
  on content.post_versions (status, review_due_at);

alter table content.posts
  add column published_version_id uuid;

alter table content.posts
  add constraint fk_content_posts_published_version
  foreign key (published_version_id)
  references content.post_versions (id)
  on delete set null;

create table content.post_sources (
  post_version_id uuid not null,
  source_id uuid not null,
  document_version_id uuid,
  locator text not null,
  quote text,
  sort_order integer default 0 not null,
  id uuid default gen_random_uuid() not null,
  constraint pk_post_sources primary key (id),
  constraint ck_post_sources_sort_order_nonnegative check (sort_order >= 0),
  constraint fk_post_sources_post_version_id_post_versions
    foreign key (post_version_id)
    references content.post_versions (id) on delete cascade,
  constraint fk_post_sources_source_id_sources
    foreign key (source_id) references knowledge.sources (id) on delete restrict,
  constraint fk_post_sources_document_version_id_document_versions
    foreign key (document_version_id)
    references knowledge.document_versions (id) on delete set null,
  constraint uq_content_post_source_locator
    unique (post_version_id, source_id, locator)
);

create index ix_content_post_sources_post_version_id
  on content.post_sources (post_version_id);
create index ix_content_post_sources_source_id
  on content.post_sources (source_id);

create table content.post_relations (
  post_id uuid not null,
  related_post_id uuid not null,
  relation_type varchar(20) not null,
  sort_order integer default 0 not null,
  constraint pk_post_relations
    primary key (post_id, related_post_id, relation_type),
  constraint ck_post_relations_not_self_referential
    check (post_id <> related_post_id),
  constraint ck_post_relations_relation_type_allowed
    check (relation_type in ('related', 'next', 'previous')),
  constraint ck_post_relations_sort_order_nonnegative
    check (sort_order >= 0),
  constraint fk_post_relations_post_id_posts
    foreign key (post_id) references content.posts (id) on delete cascade,
  constraint fk_post_relations_related_post_id_posts
    foreign key (related_post_id) references content.posts (id) on delete cascade
);

create table content.media_assets (
  storage_key text not null,
  public_url text,
  mime_type varchar(160) not null,
  byte_size integer not null,
  checksum_sha256 varchar(64) not null,
  alt_text varchar(500) not null,
  created_by_principal_id uuid not null,
  id uuid default gen_random_uuid() not null,
  created_at timestamptz default now() not null,
  constraint pk_media_assets primary key (id),
  constraint ck_media_assets_byte_size_positive check (byte_size > 0),
  constraint fk_media_assets_created_by_principal_id_principals
    foreign key (created_by_principal_id)
    references identity.principals (id) on delete restrict,
  constraint uq_media_assets_storage_key unique (storage_key)
);

create table content.publication_records (
  post_id uuid not null,
  post_version_id uuid not null,
  prior_version_id uuid,
  published_by_principal_id uuid not null,
  published_at timestamptz default now() not null,
  id uuid default gen_random_uuid() not null,
  constraint pk_publication_records primary key (id),
  constraint fk_publication_records_post_id_posts
    foreign key (post_id) references content.posts (id) on delete cascade,
  constraint fk_publication_records_post_version_id_post_versions
    foreign key (post_version_id)
    references content.post_versions (id) on delete restrict,
  constraint fk_publication_records_prior_version_id_post_versions
    foreign key (prior_version_id)
    references content.post_versions (id) on delete set null,
  constraint fk_publication_records_published_by_principal_id_principals
    foreign key (published_by_principal_id)
    references identity.principals (id) on delete restrict,
  constraint uq_publication_records_post_version_id unique (post_version_id)
);

create index ix_content_publication_records_post_id
  on content.publication_records (post_id);
create index ix_content_publication_records_published_at
  on content.publication_records (published_at);

create or replace function content.guard_post_version_update()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.status = 'draft'
     and new.status not in ('draft', 'in_review') then
    raise exception 'invalid content revision transition: % -> %',
      old.status, new.status;
  elsif old.status = 'in_review'
        and new.status not in ('in_review', 'draft', 'approved') then
    raise exception 'invalid content revision transition: % -> %',
      old.status, new.status;
  elsif old.status = 'approved'
        and new.status not in ('approved', 'draft', 'published') then
    raise exception 'invalid content revision transition: % -> %',
      old.status, new.status;
  elsif old.status = 'published'
        and new.status not in ('published', 'stale', 'archived') then
    raise exception 'invalid content revision transition: % -> %',
      old.status, new.status;
  elsif old.status = 'stale'
        and new.status not in ('stale', 'archived') then
    raise exception 'invalid content revision transition: % -> %',
      old.status, new.status;
  elsif old.status = 'archived' and new.status <> 'archived' then
    raise exception 'archived content revisions are immutable';
  end if;

  if old.status <> 'draft' and (
    new.title is distinct from old.title
    or new.summary is distinct from old.summary
    or new.body_markdown is distinct from old.body_markdown
    or new.structured_content is distinct from old.structured_content
    or new.seo_title is distinct from old.seo_title
    or new.seo_description is distinct from old.seo_description
    or new.canonical_url is distinct from old.canonical_url
    or new.hero_image_url is distinct from old.hero_image_url
    or new.hero_image_alt is distinct from old.hero_image_alt
    or new.author_id is distinct from old.author_id
    or new.checksum_sha256 is distinct from old.checksum_sha256
  ) then
    raise exception 'non-draft content revisions cannot be edited';
  end if;

  return new;
end;
$$;

create trigger trg_content_post_versions_guard
before update on content.post_versions
for each row execute function content.guard_post_version_update();

revoke all on schema content from public;

alter table content.authors enable row level security;
alter table content.posts enable row level security;
alter table content.post_versions enable row level security;
alter table content.post_sources enable row level security;
alter table content.post_relations enable row level security;
alter table content.media_assets enable row level security;
alter table content.publication_records enable row level security;

revoke all privileges on table content.authors from public;
revoke all privileges on table content.posts from public;
revoke all privileges on table content.post_versions from public;
revoke all privileges on table content.post_sources from public;
revoke all privileges on table content.post_relations from public;
revoke all privileges on table content.media_assets from public;
revoke all privileges on table content.publication_records from public;

do $$
declare
  role_name text;
begin
  foreach role_name in array array['anon', 'authenticated', 'service_role']
  loop
    if exists (select 1 from pg_roles where rolname = role_name) then
      execute format('revoke all on schema content from %I', role_name);
      execute format(
        'revoke all privileges on all tables in schema content from %I',
        role_name
      );
    end if;
  end loop;
end;
$$;

alter default privileges in schema content
revoke all privileges on tables from public;

update public.alembic_version
set version_num = '20260831_0010'
where version_num = '20260825_0009';

do $$
begin
  if not exists (
    select 1
    from public.alembic_version
    where version_num = '20260831_0010'
  ) then
    raise exception 'Failed to advance the Alembic migration ledger.';
  end if;
end;
$$;

commit;
