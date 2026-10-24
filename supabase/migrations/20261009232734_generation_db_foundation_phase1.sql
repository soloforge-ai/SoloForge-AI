-- Additive P2-B1 Phase 1 only. Prerequisites: auth.users(id uuid),
-- public.content_jobs(id uuid), public.pollinations_sessions(session_id text UNIQUE),
-- and Supabase roles. No historical replay, credentials, RPC or executor.
begin;

create schema generation_internal;
revoke all on schema generation_internal from public, anon, authenticated, service_role;

create table public.generation_budget_accounts (
    id uuid primary key default gen_random_uuid(),
    owner_user_id uuid not null references auth.users(id) on delete restrict,
    pollinations_session_id text not null references public.pollinations_sessions(session_id) on delete restrict,
    provider_wallet_fingerprint text not null check (provider_wallet_fingerprint ~ '^[0-9a-f]{64}$'),
    wallet_category text not null check (wallet_category in ('QUEST', 'PAID')),
    auth_mode text not null default 'OAUTH_OWNER' check (auth_mode = 'OAUTH_OWNER'),
    owner_session_verified_at timestamptz not null,
    allocation_state text not null default 'UNALLOCATED' check (allocation_state in ('UNALLOCATED','ALLOCATED','SUSPENDED','CLOSED')),
    allocation_ref text,
    allocation_verified_at timestamptz,
    allocated_pollen numeric(20,8) not null default 0 check (allocated_pollen >= 0 and allocated_pollen < 'Infinity'::numeric),
    reserved_pollen numeric(20,8) not null default 0 check (reserved_pollen >= 0 and reserved_pollen < 'Infinity'::numeric),
    spent_pollen numeric(20,8) not null default 0 check (spent_pollen >= 0 and spent_pollen < 'Infinity'::numeric),
    revision bigint not null default 0 check (revision >= 0),
    created_at timestamptz not null default now(),
    unique (id, owner_user_id, pollinations_session_id),
    unique (owner_user_id, provider_wallet_fingerprint, wallet_category),
    check (length(btrim(pollinations_session_id)) > 0),
    check (reserved_pollen + spent_pollen <= allocated_pollen),
    check (allocation_ref is null or length(btrim(allocation_ref)) > 0),
    check (allocation_state <> 'UNALLOCATED' or
           (allocated_pollen = 0 and reserved_pollen = 0 and spent_pollen = 0)),
    check (allocation_state <> 'ALLOCATED' or
           (allocated_pollen > 0 and allocation_ref is not null and allocation_verified_at is not null))
);

create table public.generation_approvals (
    id uuid primary key default gen_random_uuid(),
    approval_key text not null unique check (length(btrim(approval_key)) > 0),
    budget_account_id uuid not null,
    owner_user_id uuid not null,
    pollinations_session_id text not null,
    content_job_id uuid not null references public.content_jobs(id) on delete restrict,
    content_job_revision text not null check (length(btrim(content_job_revision)) > 0),
    skill_id text not null check (skill_id = 'SALES_CAROUSEL_4_V1'),
    skill_version text not null check (length(btrim(skill_version)) > 0),
    snapshot_digest text not null check (snapshot_digest ~ '^[0-9a-f]{64}$'),
    snapshot_json jsonb not null check (jsonb_typeof(snapshot_json) = 'object'),
    reference_snapshot jsonb not null check (jsonb_typeof(reference_snapshot) = 'array' and jsonb_array_length(reference_snapshot) > 0),
    request_count smallint not null check (request_count = 4),
    max_pollen numeric(20,8) not null check (max_pollen > 0 and max_pollen < 'Infinity'::numeric),
    quote_version text not null check (length(btrim(quote_version)) > 0),
    quote_expires_at timestamptz not null,
    approved_at timestamptz not null default now(),
    expires_at timestamptz not null,
    revoked_at timestamptz,
    state text not null default 'APPROVED' check (state in ('APPROVED','CLAIMED','REVOKED','EXPIRED','RECONCILE_REQUIRED','CLOSED')),
    revision bigint not null default 0 check (revision >= 0),
    created_at timestamptz not null default now(),
    foreign key (budget_account_id, owner_user_id, pollinations_session_id)
        references public.generation_budget_accounts(id, owner_user_id, pollinations_session_id) on delete restrict,
    unique (id, budget_account_id, owner_user_id, pollinations_session_id, snapshot_digest),
    check (expires_at > approved_at and quote_expires_at >= expires_at),
    check ((state = 'REVOKED') = (revoked_at is not null))
);

create table public.generation_executions (
    id uuid primary key default gen_random_uuid(),
    approval_id uuid not null unique,
    execution_key text not null unique check (length(btrim(execution_key)) > 0),
    budget_account_id uuid not null,
    owner_user_id uuid not null,
    pollinations_session_id text not null,
    snapshot_digest text not null check (snapshot_digest ~ '^[0-9a-f]{64}$'),
    snapshot_json jsonb not null check (jsonb_typeof(snapshot_json) = 'object'),
    state text not null default 'CLAIMED' check (state in ('CLAIMED','CALL_STARTED','SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_RECONCILE')),
    reserved_pollen numeric(20,8) not null check (reserved_pollen > 0 and reserved_pollen < 'Infinity'::numeric),
    observed_pollen numeric(20,8) check (observed_pollen >= 0 and observed_pollen < 'Infinity'::numeric),
    claim_time timestamptz not null default now(),
    call_started_at timestamptz,
    settled_at timestamptz,
    revision bigint not null default 0 check (revision >= 0),
    foreign key (approval_id, budget_account_id, owner_user_id, pollinations_session_id, snapshot_digest)
        references public.generation_approvals(id, budget_account_id, owner_user_id, pollinations_session_id, snapshot_digest) on delete restrict,
    unique (id, budget_account_id, owner_user_id, pollinations_session_id),
    check (state = 'CLAIMED' or call_started_at is not null),
    check (call_started_at is null or call_started_at >= claim_time),
    check (settled_at is null or (call_started_at is not null and settled_at >= call_started_at)),
    check (state not in ('SUCCEEDED','FAILED_CONFIRMED') or settled_at is not null)
);

create table public.generation_requests (
    id uuid primary key default gen_random_uuid(),
    execution_id uuid not null,
    budget_account_id uuid not null,
    owner_user_id uuid not null,
    pollinations_session_id text not null,
    slide_ordinal smallint not null check (slide_ordinal between 1 and 4),
    request_key text not null unique check (length(btrim(request_key)) > 0),
    request_snapshot jsonb not null check (jsonb_typeof(request_snapshot) = 'object'),
    max_pollen numeric(20,8) not null check (max_pollen > 0 and max_pollen < 'Infinity'::numeric),
    state text not null default 'PENDING' check (state in ('PENDING','CALL_STARTED','SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_RECONCILE')),
    call_started_at timestamptz,
    completed_at timestamptz,
    provider_request_ref text,
    observed_pollen numeric(20,8) check (observed_pollen >= 0 and observed_pollen < 'Infinity'::numeric),
    output_bucket text,
    output_object_key text,
    output_object_version text,
    output_sha256 text check (output_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    foreign key (execution_id, budget_account_id, owner_user_id, pollinations_session_id)
        references public.generation_executions(id, budget_account_id, owner_user_id, pollinations_session_id) on delete restrict,
    unique (execution_id, slide_ordinal),
    unique (id, execution_id),
    unique (output_bucket, output_object_key, output_object_version),
    check (state = 'PENDING' or call_started_at is not null),
    check (call_started_at is null or call_started_at >= created_at),
    check (completed_at is null or (call_started_at is not null and completed_at >= call_started_at)),
    check ((output_bucket is null and output_object_key is null and output_object_version is null and output_sha256 is null)
        or (length(btrim(output_bucket)) > 0 and length(btrim(output_object_key)) > 0
            and length(btrim(output_object_version)) > 0 and output_sha256 is not null
            and output_bucket is not null and output_object_key is not null and output_object_version is not null)),
    check (state <> 'SUCCEEDED' or (completed_at is not null and output_sha256 is not null)),
    check (state <> 'FAILED_CONFIRMED' or completed_at is not null)
);

create table public.generation_budget_ledger (
    id uuid primary key default gen_random_uuid(),
    execution_id uuid not null,
    budget_account_id uuid not null,
    owner_user_id uuid not null,
    pollinations_session_id text not null,
    entry_key text not null unique check (length(btrim(entry_key)) > 0),
    entry_kind text not null check (entry_kind in ('RESERVE','SETTLE','RELEASE_AFTER_VERIFICATION','MANUAL_ADJUST')),
    amount_pollen numeric(20,8) not null check (amount_pollen >= 0 and amount_pollen < 'Infinity'::numeric),
    evidence_ref text,
    created_at timestamptz not null default now(),
    foreign key (execution_id, budget_account_id, owner_user_id, pollinations_session_id)
        references public.generation_executions(id, budget_account_id, owner_user_id, pollinations_session_id) on delete restrict,
    unique (execution_id, entry_kind),
    check (entry_kind <> 'RESERVE' or amount_pollen > 0),
    check (entry_kind not in ('RELEASE_AFTER_VERIFICATION','MANUAL_ADJUST') or
           (evidence_ref is not null and length(btrim(evidence_ref)) > 0))
);

create table public.generation_events (
    id uuid primary key default gen_random_uuid(),
    execution_id uuid not null,
    budget_account_id uuid not null,
    owner_user_id uuid not null,
    pollinations_session_id text not null,
    request_id uuid,
    event_key text not null unique check (length(btrim(event_key)) > 0),
    event_type text not null check (event_type in ('CLAIMED','CALL_STARTED','SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_RECONCILE','RECONCILED','BUDGET_RESERVED','BUDGET_SETTLED','BUDGET_RELEASED')),
    safe_detail jsonb not null default '{}'::jsonb check (jsonb_typeof(safe_detail) = 'object'),
    created_at timestamptz not null default now(),
    foreign key (execution_id, budget_account_id, owner_user_id, pollinations_session_id)
        references public.generation_executions(id, budget_account_id, owner_user_id, pollinations_session_id) on delete restrict,
    foreign key (request_id, execution_id) references public.generation_requests(id, execution_id) on delete restrict
);

-- Index leading FK keys not already covered by PK/unique indexes.
create index generation_budget_accounts_owner_idx on public.generation_budget_accounts(owner_user_id);
create index generation_budget_accounts_session_idx on public.generation_budget_accounts(pollinations_session_id);
create index generation_approvals_account_idx on public.generation_approvals(budget_account_id, owner_user_id, pollinations_session_id);
create index generation_approvals_job_idx on public.generation_approvals(content_job_id);
create index generation_approvals_pending_idx on public.generation_approvals(expires_at) where state = 'APPROVED';
create index generation_executions_account_idx on public.generation_executions(budget_account_id);
create index generation_executions_reconcile_idx on public.generation_executions(claim_time) where state in ('CLAIMED','CALL_STARTED','UNKNOWN_RECONCILE');
create index generation_budget_ledger_account_idx on public.generation_budget_ledger(budget_account_id, created_at);
create index generation_events_execution_idx on public.generation_events(execution_id, created_at);
create index generation_events_request_idx on public.generation_events(request_id, execution_id);
create index generation_events_account_idx on public.generation_events(budget_account_id);

-- Trigger-only helpers, not callable business RPCs.
create function generation_internal.guard_immutable() returns trigger
language plpgsql security invoker set search_path = pg_catalog as $$
begin
    if TG_OP = 'DELETE' or TG_ARGV[0] = '' then
        raise exception 'generation audit rows cannot be changed or deleted' using errcode = '23514';
    end if;
    if (to_jsonb(NEW) - string_to_array(TG_ARGV[0], ',')) is distinct from
       (to_jsonb(OLD) - string_to_array(TG_ARGV[0], ',')) then
        raise exception 'generation binding and snapshot are immutable' using errcode = '23514';
    end if;
    if TG_TABLE_NAME in ('generation_executions','generation_requests') then
        if NEW.state <> OLD.state then
            if not ((OLD.state in ('CLAIMED','PENDING') and NEW.state = 'CALL_STARTED') or
                    (OLD.state = 'CALL_STARTED' and NEW.state in ('SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_RECONCILE')) or
                    (OLD.state = 'UNKNOWN_RECONCILE' and NEW.state in ('SUCCEEDED','FAILED_CONFIRMED'))) then
                raise exception 'unsafe generation state transition; reconciliation required' using errcode = '23514';
            end if;
        end if;
        if OLD.call_started_at is not null and NEW.call_started_at is distinct from OLD.call_started_at then
            raise exception 'call start is immutable once recorded' using errcode = '23514';
        end if;
    end if;
    if TG_TABLE_NAME = 'generation_requests' then
        if OLD.output_sha256 is not null and
           (NEW.output_bucket,NEW.output_object_key,NEW.output_object_version,NEW.output_sha256) is distinct from
           (OLD.output_bucket,OLD.output_object_key,OLD.output_object_version,OLD.output_sha256) then
            raise exception 'output storage reference is immutable' using errcode = '23514';
        end if;
    end if;
    return NEW;
end;
$$;

create function generation_internal.validate_snapshot() returns trigger
language plpgsql security invoker set search_path = pg_catalog as $$
declare
    reference jsonb;
    parent_snapshot jsonb;
begin
    if TG_TABLE_NAME = 'generation_approvals' then
        if not (NEW.snapshot_json ?& array['slides','model_id','model_mapping_version','dimensions','storyboard_sha256']) or
           jsonb_typeof(NEW.snapshot_json->'slides') is distinct from 'array' or
           jsonb_array_length(NEW.snapshot_json->'slides') <> NEW.request_count then
            raise exception 'snapshot requires complete immutable batch fields' using errcode = '23514';
        end if;
        for reference in select value from jsonb_array_elements(NEW.reference_snapshot) loop
            if jsonb_typeof(reference) is distinct from 'object' or
               not (reference ?& array['bucket','object_key','object_version','sha256']) or
               coalesce(reference->>'sha256','') !~ '^[0-9a-f]{64}$' or
               coalesce(length(btrim(reference->>'bucket')),0) = 0 or
               coalesce(length(btrim(reference->>'object_key')),0) = 0 or
               coalesce(length(btrim(reference->>'object_version')),0) = 0 then
                raise exception 'immutable storage reference required' using errcode = '23514';
            end if;
        end loop;
    elsif TG_TABLE_NAME = 'generation_executions' then
        select snapshot_json into parent_snapshot from public.generation_approvals where id = NEW.approval_id;
        if parent_snapshot is not null and NEW.snapshot_json is distinct from parent_snapshot then
            raise exception 'execution snapshot differs from approval' using errcode = '23514';
        end if;
    elsif TG_TABLE_NAME = 'generation_requests' then
        select snapshot_json->'slides'->(NEW.slide_ordinal - 1) into parent_snapshot
            from public.generation_executions where id = NEW.execution_id;
        if parent_snapshot is not null and NEW.request_snapshot is distinct from parent_snapshot then
            raise exception 'request snapshot differs from approved slide' using errcode = '23514';
        end if;
    end if;
    return NEW;
end;
$$;

create trigger generation_accounts_immutable before update or delete on public.generation_budget_accounts
for each row execute function generation_internal.guard_immutable('allocation_state,allocation_ref,allocation_verified_at,allocated_pollen,reserved_pollen,spent_pollen,revision');
create trigger generation_approvals_immutable before update or delete on public.generation_approvals
for each row execute function generation_internal.guard_immutable('state,revoked_at,revision');
create trigger generation_executions_immutable before update or delete on public.generation_executions
for each row execute function generation_internal.guard_immutable('state,observed_pollen,call_started_at,settled_at,revision');
create trigger generation_requests_immutable before update or delete on public.generation_requests
for each row execute function generation_internal.guard_immutable('state,call_started_at,completed_at,provider_request_ref,observed_pollen,output_bucket,output_object_key,output_object_version,output_sha256');
create trigger generation_ledger_immutable before update or delete on public.generation_budget_ledger
for each row execute function generation_internal.guard_immutable('');
create trigger generation_events_immutable before update or delete on public.generation_events
for each row execute function generation_internal.guard_immutable('');
create trigger generation_approval_snapshot before insert on public.generation_approvals
for each row execute function generation_internal.validate_snapshot();
create trigger generation_execution_snapshot before insert on public.generation_executions
for each row execute function generation_internal.validate_snapshot();
create trigger generation_request_snapshot before insert on public.generation_requests
for each row execute function generation_internal.validate_snapshot();

revoke all on all functions in schema generation_internal from public, anon, authenticated, service_role;

alter table public.generation_budget_accounts enable row level security;
alter table public.generation_budget_accounts force row level security;
alter table public.generation_approvals enable row level security;
alter table public.generation_approvals force row level security;
alter table public.generation_executions enable row level security;
alter table public.generation_executions force row level security;
alter table public.generation_requests enable row level security;
alter table public.generation_requests force row level security;
alter table public.generation_budget_ledger enable row level security;
alter table public.generation_budget_ledger force row level security;
alter table public.generation_events enable row level security;
alter table public.generation_events force row level security;

revoke all on public.generation_budget_accounts, public.generation_approvals,
    public.generation_executions, public.generation_requests,
    public.generation_budget_ledger, public.generation_events from public, anon, authenticated, service_role;
grant select, insert on public.generation_budget_accounts, public.generation_approvals,
    public.generation_executions, public.generation_requests,
    public.generation_budget_ledger, public.generation_events to service_role;
grant update (allocation_state,allocation_ref,allocation_verified_at,allocated_pollen,reserved_pollen,spent_pollen,revision)
    on public.generation_budget_accounts to service_role;
grant update (state,revoked_at,revision) on public.generation_approvals to service_role;
grant update (state,observed_pollen,call_started_at,settled_at,revision) on public.generation_executions to service_role;
grant update (state,call_started_at,completed_at,provider_request_ref,observed_pollen,output_bucket,output_object_key,output_object_version,output_sha256)
    on public.generation_requests to service_role;
commit;