-- Editable account details and private, owner-scoped profile images.
alter table public.profiles
  add column if not exists first_name text check (char_length(first_name) <= 80),
  add column if not exists last_name text check (char_length(last_name) <= 80),
  add column if not exists avatar_path text check (
    avatar_path is null or avatar_path = user_id::text || '/avatar'
  );

revoke update on public.profiles from authenticated;
grant update (
  first_name,
  last_name,
  display_name,
  preferred_language,
  nationality,
  resident_status,
  avatar_path
) on public.profiles to authenticated;

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'avatars',
  'avatars',
  false,
  2097152,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "avatars_select_own" on storage.objects;
create policy "avatars_select_own"
on storage.objects for select
to authenticated
using (
  bucket_id = 'avatars'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "avatars_insert_own" on storage.objects;
create policy "avatars_insert_own"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'avatars'
  and name = (select auth.uid())::text || '/avatar'
);

drop policy if exists "avatars_update_own" on storage.objects;
create policy "avatars_update_own"
on storage.objects for update
to authenticated
using (
  bucket_id = 'avatars'
  and name = (select auth.uid())::text || '/avatar'
)
with check (
  bucket_id = 'avatars'
  and name = (select auth.uid())::text || '/avatar'
);

drop policy if exists "avatars_delete_own" on storage.objects;
create policy "avatars_delete_own"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'avatars'
  and name = (select auth.uid())::text || '/avatar'
);
