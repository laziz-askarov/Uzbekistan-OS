-- Supabase public-schema defaults are broader than this profile boundary needs.
revoke all privileges on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (display_name, preferred_language, nationality, resident_status)
on public.profiles to authenticated;
