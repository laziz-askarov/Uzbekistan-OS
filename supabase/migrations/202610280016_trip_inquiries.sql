-- Trip-planning inquiries submitted on /trips. Visitors are not signed in, so
-- rows are written only by the server with the service role; staff read them
-- through the admin client. No anon or authenticated access exists.

create table public.trip_inquiries (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  status text not null default 'new'
    check (status in ('new', 'replied', 'closed', 'spam')),
  name text not null check (char_length(name) between 1 and 120),
  email text not null check (char_length(email) between 3 and 200),
  travel_month text not null check (travel_month ~ '^\d{4}-(0[1-9]|1[0-2])$'),
  nights integer not null check (nights between 1 and 60),
  travellers integer not null check (travellers between 1 and 20),
  interests text[] not null default '{}',
  comfort text not null check (comfort in ('simple', 'comfortable', 'premium')),
  budget text not null
    check (budget in ('under-120', '120-200', '200-350', '350-plus', 'not-sure')),
  message text not null default '' check (char_length(message) <= 2000),
  source_path text check (source_path is null or char_length(source_path) <= 200),
  request_id text check (request_id is null or char_length(request_id) <= 128),
  handled_by uuid references auth.users(id) on delete set null,
  handled_at timestamptz
);

comment on table public.trip_inquiries is
  'Trip-planning inquiries for Kebab Travel. Personal data: retained 24 months after the last status change, then deleted.';

create index trip_inquiries_created_at_idx
  on public.trip_inquiries (created_at desc);
create index trip_inquiries_email_created_at_idx
  on public.trip_inquiries (email, created_at desc);
create index trip_inquiries_status_idx
  on public.trip_inquiries (status, created_at desc);

alter table public.trip_inquiries enable row level security;
revoke all privileges on public.trip_inquiries from public, anon, authenticated;
