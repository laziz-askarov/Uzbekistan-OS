-- Durable per-account quotas for the cost-bearing AI chat route.
create table if not exists public.abuse_rate_limits (
  user_id uuid not null references auth.users(id) on delete cascade,
  scope text not null check (scope in ('chat_10_minutes', 'chat_day')),
  window_start timestamptz not null,
  request_count integer not null default 0 check (request_count >= 0),
  updated_at timestamptz not null default now(),
  primary key (user_id, scope, window_start)
);

alter table public.abuse_rate_limits enable row level security;
revoke all privileges on public.abuse_rate_limits from anon, authenticated;

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
  current_time timestamptz := statement_timestamp();
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
    floor(extract(epoch from current_time) / 600) * 600
  );
  daily_window := date_trunc('day', current_time);

  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(current_user_id::text, 0)
  );

  delete from public.abuse_rate_limits
  where user_id = current_user_id
    and window_start < current_time - interval '2 days';

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
        ceil(extract(epoch from short_window + interval '10 minutes' - current_time))::integer
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
        ceil(extract(epoch from daily_window + interval '1 day' - current_time))::integer
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
    updated_at = current_time;

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
    updated_at = current_time;

  return query select
    true,
    least(short_limit - short_count - 1, daily_limit - daily_count - 1),
    0,
    null::text;
end;
$$;

revoke all on function public.consume_chat_quota() from public, anon;
grant execute on function public.consume_chat_quota() to authenticated;
