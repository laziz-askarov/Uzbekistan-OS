-- Durable per-account quotas for feedback and account-export actions.
alter table public.abuse_rate_limits
  drop constraint if exists abuse_rate_limits_scope_check;

alter table public.abuse_rate_limits
  add constraint abuse_rate_limits_scope_check check (
    scope in (
      'chat_10_minutes',
      'chat_day',
      'feedback_hour',
      'account_export_hour'
    )
  );

create or replace function public.consume_action_quota(requested_scope text)
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
  current_window timestamptz := date_trunc('hour', current_time);
  current_count integer;
  action_limit integer;
begin
  if current_user_id is null then
    raise insufficient_privilege using message = 'Authentication required';
  end if;

  action_limit := case requested_scope
    when 'feedback_hour' then 10
    when 'account_export_hour' then 3
    else null
  end;
  if action_limit is null then
    raise invalid_parameter_value using message = 'Unsupported rate limit scope';
  end if;

  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(
      current_user_id::text || ':' || requested_scope,
      0
    )
  );

  delete from public.abuse_rate_limits
  where user_id = current_user_id
    and window_start < current_time - interval '2 days';

  select coalesce(request_count, 0)
  into current_count
  from public.abuse_rate_limits
  where user_id = current_user_id
    and scope = requested_scope
    and window_start = current_window;
  current_count := coalesce(current_count, 0);

  if current_count >= action_limit then
    return query select
      false,
      0,
      greatest(
        1,
        ceil(extract(epoch from current_window + interval '1 hour' - current_time))::integer
      ),
      requested_scope;
    return;
  end if;

  insert into public.abuse_rate_limits (
    user_id,
    scope,
    window_start,
    request_count
  ) values (
    current_user_id,
    requested_scope,
    current_window,
    1
  )
  on conflict (user_id, scope, window_start) do update set
    request_count = public.abuse_rate_limits.request_count + 1,
    updated_at = current_time;

  return query select
    true,
    action_limit - current_count - 1,
    0,
    requested_scope;
end;
$$;

revoke all on function public.consume_action_quota(text) from public, anon;
grant execute on function public.consume_action_quota(text) to authenticated;
