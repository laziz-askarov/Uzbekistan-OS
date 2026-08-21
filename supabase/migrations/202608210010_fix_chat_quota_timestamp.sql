-- Use an unambiguous timestamp variable when calculating quota windows.
create or replace function public.consume_chat_quota()
returns table (
  allowed boolean,
  remaining integer,
  retry_after_seconds integer,
  limit_scope text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_user_id uuid := (select auth.uid());
  request_time timestamptz := statement_timestamp();
  short_window timestamptz;
  daily_window timestamptz;
  short_count integer;
  daily_count integer;
  short_limit constant integer := 20;
  daily_limit constant integer := 100;
begin
  if current_user_id is null then
    raise insufficient_privilege using message = 'Authentication required';
  end if;

  short_window := to_timestamp(
    floor(extract(epoch from request_time) / 600) * 600
  );
  daily_window := date_trunc('day', request_time);

  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(current_user_id::text, 0)
  );

  delete from public.abuse_rate_limits
  where user_id = current_user_id
    and window_start < request_time - interval '2 days';

  select coalesce(request_count, 0)
  into short_count
  from public.abuse_rate_limits
  where user_id = current_user_id
    and scope = 'chat_10_minutes'
    and window_start = short_window;
  short_count := coalesce(short_count, 0);

  select coalesce(request_count, 0)
  into daily_count
  from public.abuse_rate_limits
  where user_id = current_user_id
    and scope = 'chat_day'
    and window_start = daily_window;
  daily_count := coalesce(daily_count, 0);

  if short_count >= short_limit then
    return query select
      false,
      0,
      greatest(
        1,
        ceil(extract(epoch from short_window + interval '10 minutes' - request_time))::integer
      ),
      'chat_10_minutes'::text;
    return;
  end if;

  if daily_count >= daily_limit then
    return query select
      false,
      0,
      greatest(
        1,
        ceil(extract(epoch from daily_window + interval '1 day' - request_time))::integer
      ),
      'chat_day'::text;
    return;
  end if;

  insert into public.abuse_rate_limits (
    user_id,
    scope,
    window_start,
    request_count
  ) values (
    current_user_id,
    'chat_10_minutes',
    short_window,
    1
  )
  on conflict (user_id, scope, window_start) do update set
    request_count = public.abuse_rate_limits.request_count + 1,
    updated_at = request_time;

  insert into public.abuse_rate_limits (
    user_id,
    scope,
    window_start,
    request_count
  ) values (
    current_user_id,
    'chat_day',
    daily_window,
    1
  )
  on conflict (user_id, scope, window_start) do update set
    request_count = public.abuse_rate_limits.request_count + 1,
    updated_at = request_time;

  return query select
    true,
    least(short_limit - short_count - 1, daily_limit - daily_count - 1),
    0,
    null::text;
end;
$$;

revoke all on function public.consume_chat_quota() from public, anon;
grant execute on function public.consume_chat_quota() to authenticated;
