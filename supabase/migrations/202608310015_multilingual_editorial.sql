-- Enforce one editorial post per language in each translation group.
--
-- This is the Supabase SQL Editor companion to API Alembic revision
-- 20260831_0012. Run the whole file as one query.

begin;

do $$
declare
  current_revision text;
begin
  if to_regclass('public.alembic_version') is null then
    raise exception
      'Missing public.alembic_version. Apply API migrations through 20260831_0011 first.';
  end if;

  select version_num into current_revision
  from public.alembic_version
  limit 1;

  if current_revision = '20260831_0012' then
    raise exception 'Multilingual editorial migration 20260831_0012 is already applied.';
  end if;

  if current_revision is distinct from '20260831_0011' then
    raise exception
      'Expected Alembic revision 20260831_0011, found %.',
      coalesce(current_revision, '<none>');
  end if;

  if exists (
    select 1
    from content.posts
    group by translation_group_id, language_id
    having count(*) > 1
  ) then
    raise exception
      'Duplicate languages exist inside an editorial translation group. Resolve them before retrying.';
  end if;
end;
$$;

alter table content.posts
  add constraint uq_content_posts_translation_language
  unique (translation_group_id, language_id);

update public.alembic_version
set version_num = '20260831_0012'
where version_num = '20260831_0011';

do $$
begin
  if not exists (
    select 1 from public.alembic_version
    where version_num = '20260831_0012'
  ) then
    raise exception 'Failed to advance the Alembic migration ledger.';
  end if;
end;
$$;

commit;
