-- Treat a verified email as the launch account's verified contact method.
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
    case
      when new.phone_confirmed_at is not null or new.email_confirmed_at is not null then 2
      when coalesce(new.is_anonymous, false) then 0
      else 1
    end
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
create trigger on_auth_user_synced
after insert or update of phone, email, phone_confirmed_at, email_confirmed_at, raw_user_meta_data
on auth.users
for each row execute procedure public.sync_auth_profile();
