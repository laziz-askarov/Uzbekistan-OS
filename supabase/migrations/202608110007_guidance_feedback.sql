-- User reports for incorrect, outdated, or unclear assistant guidance.
-- Admin access is intentionally deferred until account roles are introduced;
-- the service role can read this queue for future admin tooling.
create table if not exists public.guidance_feedback (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references auth.users(id) on delete cascade,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  message_id uuid not null references public.messages(id) on delete cascade,
  category text not null check (category in ('incorrect', 'outdated', 'unclear', 'other')),
  details text check (details is null or char_length(details) between 1 and 1200),
  status text not null default 'new' check (status in ('new', 'reviewing', 'resolved', 'dismissed')),
  admin_notes text check (admin_notes is null or char_length(admin_notes) <= 4000),
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (reporter_id, message_id)
);

create index if not exists guidance_feedback_status_created_idx
on public.guidance_feedback(status, created_at desc);

create index if not exists guidance_feedback_reporter_created_idx
on public.guidance_feedback(reporter_id, created_at desc);

alter table public.guidance_feedback enable row level security;

drop policy if exists "guidance_feedback_insert_own"
on public.guidance_feedback;

create policy "guidance_feedback_insert_own"
on public.guidance_feedback for insert
to authenticated
with check (
  (select auth.uid()) = reporter_id
  and exists (
    select 1
    from public.messages message
    where message.id = public.guidance_feedback.message_id
      and message.conversation_id = public.guidance_feedback.conversation_id
      and message.owner_id = (select auth.uid())
      and message.role = 'assistant'
  )
);

revoke all privileges on public.guidance_feedback from anon, authenticated;
grant insert (reporter_id, conversation_id, message_id, category, details)
on public.guidance_feedback to authenticated;

comment on table public.guidance_feedback is
'Owner-submitted assistant guidance reports for a future admin review queue.';
