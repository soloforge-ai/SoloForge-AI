-- P2-B1 clean rebuild: additive schema foundation only.
-- No executor, dispatch, wallet debit or provider API invocation.
-- All generation data is service-only; execution remains locked by S1.
create table public.generation_budget_accounts (
 id uuid primary key default gen_random_uuid(),
 owner_user_id uuid not null,
 provider text not null default 'pollinations' check (provider = 'pollinations'),
 provider_subject text not null check (length(btrim(provider_subject)) > 0),
 wallet_allocation_pollen numeric(20,8) not null check (wallet_allocation_pollen >= 0),
 reserved_pollen numeric(20,8) not null default 0 check (reserved_pollen >= 0),
 spent_pollen numeric(20,8) not null default 0 check (spent_pollen >= 0),
 enabled boolean not null default false,
 created_at timestamptz not null default now(),
 unique (owner_user_id, provider, provider_subject),
 check (reserved_pollen + spent_pollen <= wallet_allocation_pollen)
);
create table public.generation_approvals (
 id uuid primary key default gen_random_uuid(),
 budget_account_id uuid not null references public.generation_budget_accounts(id),
 owner_user_id uuid not null,
 approved_models text[] not null check (cardinality(approved_models) > 0),
 max_pollen numeric(20,8) not null check (max_pollen > 0),
 expires_at timestamptz not null,
 approval_snapshot jsonb not null check (jsonb_typeof(approval_snapshot) = 'object'),
 created_at timestamptz not null default now()
);
create table public.generation_executions (
 id uuid primary key default gen_random_uuid(),
 approval_id uuid not null references public.generation_approvals(id),
 budget_account_id uuid not null references public.generation_budget_accounts(id),
 owner_user_id uuid not null,
 idempotency_key text not null check (length(btrim(idempotency_key)) > 0),
 execution_snapshot jsonb not null check (jsonb_typeof(execution_snapshot) = 'object'),
 state text not null default 'PENDING' check (state in ('PENDING','APPROVED','RUNNING','RECONCILIATION_REQUIRED','COMPLETED','FAILED','CANCELLED')),
 created_at timestamptz not null default now(),
 unique (owner_user_id,idempotency_key)
);
create table public.generation_requests (
 id uuid primary key default gen_random_uuid(),
 execution_id uuid not null references public.generation_executions(id),
 slide_index integer not null check (slide_index >= 0),
 model_id text not null check (length(btrim(model_id)) > 0),
 request_snapshot jsonb not null check (jsonb_typeof(request_snapshot) = 'object'),
 state text not null default 'PENDING' check (state in ('PENDING','CLAIMED','CALL_STARTED','RECONCILIATION_REQUIRED','SUCCEEDED','FAILED','CANCELLED')),
 provider_request_id text,
 created_at timestamptz not null default now(),
 unique (execution_id,slide_index)
);
create unique index generation_one_inflight_request_per_execution
 on public.generation_requests(execution_id)
 where state in ('CLAIMED','CALL_STARTED','RECONCILIATION_REQUIRED');
create table public.generation_budget_ledger (
 id uuid primary key default gen_random_uuid(),
 budget_account_id uuid not null references public.generation_budget_accounts(id),
 execution_id uuid not null references public.generation_executions(id),
 request_id uuid references public.generation_requests(id),
 entry_type text not null check (entry_type in ('RESERVE','SETTLE','RELEASE','ADJUST')),
 amount_pollen numeric(20,8) not null check (amount_pollen > 0),
 idempotency_key text not null check (length(btrim(idempotency_key)) > 0),
 created_at timestamptz not null default now(),
 unique (budget_account_id,idempotency_key)
);
create table public.generation_events (
 id bigint generated always as identity primary key,
 execution_id uuid not null references public.generation_executions(id),
 request_id uuid references public.generation_requests(id),
 event_type text not null check (length(btrim(event_type)) > 0),
 evidence jsonb not null default '{}'::jsonb check (jsonb_typeof(evidence) = 'object'),
 created_at timestamptz not null default now()
);
-- Deny all direct client access, including SELECT; service-only API/RPC layer will be added separately.
do $$
declare t text;
begin
 foreach t in array array[
 'generation_budget_accounts','generation_approvals','generation_executions',
 'generation_requests','generation_budget_ledger','generation_events'
 ] loop
 execute format('alter table public.%I enable row level security',t);
 execute format('revoke all on table public.%I from public, anon, authenticated',t);
 execute format('grant all on table public.%I to service_role',t);
 end loop;
end $$;
revoke all on sequence public.generation_events_id_seq from public, anon, authenticated;
grant usage, select on sequence public.generation_events_id_seq to service_role;
-- Fail closed: no SECURITY DEFINER generation RPC or executor is created by this migration.
