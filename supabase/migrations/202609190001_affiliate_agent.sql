-- SoloForge Affiliate Agent MVP schema.
-- All tables are prefixed with affiliate_ to avoid collisions with other SoloForge modules.

create extension if not exists pgcrypto;

create table if not exists public.affiliate_profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    niche text,
    audience text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.affiliate_programs (
    id uuid primary key default gen_random_uuid(),
    external_id text,
    name text not null,
    website text,
    category text,
    description text,
    commission_type text,
    commission_value numeric,
    cookie_days integer,
    recurring boolean not null default false,
    pricing text,
    free_trial boolean,
    application_url text,
    source text not null,
    source_url text,
    verified_at timestamptz,
    source_payload jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    unique(source, external_id)
);

create table if not exists public.affiliate_user_programs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    program_id uuid not null references public.affiliate_programs(id) on delete cascade,
    status text not null default 'discovered' check (status in (
        'discovered','interested','applied','approved','rejected','active','paused'
    )),
    affiliate_url text,
    joined_at timestamptz,
    notes text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    unique(user_id, program_id)
);

create table if not exists public.affiliate_opportunity_scores (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    program_id uuid not null references public.affiliate_programs(id) on delete cascade,
    audience_fit numeric(5,2) not null check (audience_fit between 0 and 100),
    content_potential numeric(5,2) not null check (content_potential between 0 and 100),
    commission_score numeric(5,2) not null check (commission_score between 0 and 100),
    product_value numeric(5,2) not null check (product_value between 0 and 100),
    competition numeric(5,2) not null check (competition between 0 and 100),
    total_score numeric(5,2) generated always as (
        audience_fit * 0.30 +
        content_potential * 0.25 +
        commission_score * 0.20 +
        product_value * 0.15 +
        competition * 0.10
    ) stored,
    rationale jsonb,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.affiliate_content_items (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    program_id uuid references public.affiliate_programs(id) on delete set null,
    title text not null,
    platform text,
    format text,
    intent text,
    goal text,
    status text not null default 'draft' check (status in (
        'draft','needs_verification','ready','published','archived'
    )),
    hooks jsonb,
    script text,
    shot_list jsonb,
    voiceover text,
    visual_prompts jsonb,
    thumbnail_brief text,
    cta text,
    description text,
    affiliate_disclosure text,
    evidence_status text not null default 'unverified' check (
        evidence_status in ('unverified','partially_verified','verified','not_required')
    ),
    published_url text,
    published_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.affiliate_content_claims (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    content_id uuid not null references public.affiliate_content_items(id) on delete cascade,
    claim_text text not null,
    claim_type text not null check (
        claim_type in ('sourced_fact','product_claim','first_hand_claim','measured_result')
    ),
    evidence_required text,
    evidence jsonb,
    verification_status text not null default 'unverified' check (
        verification_status in ('unverified','verified','rejected','not_required')
    ),
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.affiliate_content_tools (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    content_id uuid not null references public.affiliate_content_items(id) on delete cascade,
    tool_name text not null,
    role text not null,
    affiliate_url text,
    used_in_final_output boolean not null default true,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.affiliate_tracking_links (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    program_id uuid not null references public.affiliate_programs(id) on delete cascade,
    content_id uuid references public.affiliate_content_items(id) on delete set null,
    slug text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,79}$'),
    target_url text not null,
    active boolean not null default true,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.affiliate_click_events (
    id bigint generated by default as identity primary key,
    tracking_link_id uuid not null references public.affiliate_tracking_links(id) on delete cascade,
    occurred_at timestamptz not null default timezone('utc', now()),
    referrer text,
    user_agent_hash text
);

create table if not exists public.affiliate_performance_entries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    program_id uuid not null references public.affiliate_programs(id) on delete cascade,
    content_id uuid references public.affiliate_content_items(id) on delete set null,
    conversions integer not null default 0 check (conversions >= 0),
    revenue numeric(14,2) not null default 0 check (revenue >= 0),
    currency text not null default 'THB',
    period_start date not null,
    period_end date not null,
    source text not null default 'manual',
    created_at timestamptz not null default timezone('utc', now()),
    check (period_end >= period_start)
);

create index if not exists affiliate_programs_category_idx
    on public.affiliate_programs(category);
create index if not exists affiliate_user_programs_user_status_idx
    on public.affiliate_user_programs(user_id, status);
create index if not exists affiliate_scores_user_program_idx
    on public.affiliate_opportunity_scores(user_id, program_id, created_at desc);
create index if not exists affiliate_content_user_status_idx
    on public.affiliate_content_items(user_id, status, created_at desc);
create index if not exists affiliate_content_tools_content_idx
    on public.affiliate_content_tools(content_id);
create index if not exists affiliate_click_events_link_time_idx
    on public.affiliate_click_events(tracking_link_id, occurred_at desc);
create index if not exists affiliate_performance_user_program_idx
    on public.affiliate_performance_entries(user_id, program_id, period_end desc);

alter table public.affiliate_profiles enable row level security;
alter table public.affiliate_programs enable row level security;
alter table public.affiliate_user_programs enable row level security;
alter table public.affiliate_opportunity_scores enable row level security;
alter table public.affiliate_content_items enable row level security;
alter table public.affiliate_content_claims enable row level security;
alter table public.affiliate_content_tools enable row level security;
alter table public.affiliate_tracking_links enable row level security;
alter table public.affiliate_click_events enable row level security;
alter table public.affiliate_performance_entries enable row level security;

create policy "affiliate_profiles_owner_all"
on public.affiliate_profiles
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_programs_authenticated_read"
on public.affiliate_programs
for select to authenticated
using (true);

create policy "affiliate_user_programs_owner_all"
on public.affiliate_user_programs
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_scores_owner_all"
on public.affiliate_opportunity_scores
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_content_owner_all"
on public.affiliate_content_items
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_claims_owner_all"
on public.affiliate_content_claims
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_tools_owner_all"
on public.affiliate_content_tools
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_tracking_links_owner_all"
on public.affiliate_tracking_links
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "affiliate_performance_owner_all"
on public.affiliate_performance_entries
for all to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- Intentionally no authenticated policy on affiliate_click_events.
-- Click logging must be performed by a trusted server/service-role handler
-- before redirecting to target_url.

create or replace view public.affiliate_content_performance as
select
    tl.user_id,
    tl.program_id,
    tl.content_id,
    count(ce.id)::bigint as clicks
from public.affiliate_tracking_links tl
left join public.affiliate_click_events ce on ce.tracking_link_id = tl.id
group by tl.user_id, tl.program_id, tl.content_id;
