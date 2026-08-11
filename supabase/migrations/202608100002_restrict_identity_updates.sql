-- Identity trust fields are controlled only by the auth synchronization trigger.
revoke update on public.profiles from authenticated;
grant update (display_name, preferred_language, nationality, resident_status)
on public.profiles to authenticated;
