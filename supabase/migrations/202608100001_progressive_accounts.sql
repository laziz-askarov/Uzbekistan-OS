-- Progressive identity and account-owned workspace data.
create extension if not exists pgcrypto;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  phone text,
  email text,
  display_name text check (char_length(display_name) <= 100),
  preferred_language text not null default 'en' check (preferred_language in ('en', 'uz', 'ru')),
  nationality text check (char_length(nationality) <= 100),
  resident_status text check (char_length(resident_status) <= 100),
  identity_level smallint not null default 0 check (identity_level between 0 and 3),
  oneid_user_id text,
  oneid_verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint oneid_requires_verification check (
    (identity_level < 3 and oneid_user_id is null and oneid_verified_at is null)
    or (identity_level = 3 and oneid_user_id is not null and oneid_verified_at is not null)
  )
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New conversation' check (char_length(title) between 1 and 120),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists public.checklists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 160),
  items jsonb not null default '[]'::jsonb check (jsonb_typeof(items) = 'array'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists conversations_owner_updated_idx on public.conversations(owner_id, updated_at desc);
create index if not exists messages_conversation_created_idx on public.messages(conversation_id, created_at);
create index if not exists messages_owner_idx on public.messages(owner_id);
create index if not exists checklists_owner_updated_idx on public.checklists(owner_id, updated_at desc);

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.checklists enable row level security;

create policy "profiles_select_own" on public.profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy "profiles_update_own" on public.profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "conversations_own_all" on public.conversations for all to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy "messages_own_all" on public.messages for all to authenticated using ((select auth.uid()) = owner_id) with check (
  (select auth.uid()) = owner_id
  and exists (select 1 from public.conversations c where c.id = conversation_id and c.owner_id = (select auth.uid()))
);
create policy "checklists_own_all" on public.checklists for all to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);

create or replace function public.sync_auth_profile()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (user_id, phone, email, display_name, identity_level)
  values (
    new.id,
    new.phone,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    case when new.phone_confirmed_at is not null then 2 when coalesce(new.is_anonymous, false) then 0 else 1 end
  )
  on conflict (user_id) do update set
    phone = excluded.phone,
    email = excluded.email,
    display_name = coalesce(public.profiles.display_name, excluded.display_name),
    identity_level = greatest(public.profiles.identity_level, excluded.identity_level),
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_synced on auth.users;
create trigger on_auth_user_synced after insert or update of phone, email, phone_confirmed_at, raw_user_meta_data on auth.users for each row execute procedure public.sync_auth_profile();

grant usage on schema public to authenticated;
revoke all privileges on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (display_name, preferred_language, nationality, resident_status) on public.profiles to authenticated;
grant select, insert, update, delete on public.conversations, public.messages, public.checklists to authenticated;
