-- Local additive candidate only. Do not apply to production in this task.
begin;
create table public.soloforge_memberships (
    user_id uuid primary key references auth.users(id),
    status text not null default 'PENDING' check (status in ('PENDING','ACTIVE','SUSPENDED','DISABLED')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    activated_at timestamptz,
    activation_evidence jsonb,
    check (status <> 'ACTIVE' or (activated_at is not null and activation_evidence is not null))
);
alter table public.soloforge_memberships enable row level security;
-- No client activation policy. Only an authorized administrative registration
-- process can establish eligibility; the runtime receives read access only.
revoke all on public.soloforge_memberships from public, anon, authenticated, service_role;
grant select on public.soloforge_memberships to service_role;

create table public.byop_ledgers (
    principal text primary key check (principal ~ '^(owner|member):[0-9a-f-]{36}$'),
    revision bigint not null default 0,
    state jsonb not null,
    updated_at timestamptz not null default now()
);
alter table public.byop_ledgers enable row level security;
revoke all on public.byop_ledgers from public, anon, authenticated, service_role;
grant select, update on public.byop_ledgers to service_role;
-- Budget provisioning is administrative; API clients cannot top up or create a ledger.
create function public.byop_ledger_cas(p_principal text, p_revision bigint, p_state jsonb)
returns boolean language plpgsql security invoker set search_path='' as $$
declare old_state jsonb; entry record; reserved_total bigint; active_count bigint;
begin
    select state into old_state from public.byop_ledgers
        where principal=p_principal and revision=p_revision for update;
    if not found then return false; end if;
    -- Budget and concurrency policy cannot be changed by runtime CAS.
    if old_state->'budget' is distinct from p_state->'budget'
        or old_state->'concurrency_limit' is distinct from p_state->'concurrency_limit'
        or old_state->'settled' is distinct from p_state->'settled' then
        raise exception 'Administrative budget policy is immutable';
    end if;
    select coalesce(sum((value->>'reserved')::bigint),0), count(*) into reserved_total,active_count
        from jsonb_each(coalesce(p_state->'executions','{}'))
        where value->>'state' in ('RESERVED','CALL_STARTED','UNKNOWN','GENERATED');
    if reserved_total + coalesce((p_state->>'settled')::bigint,0) > (p_state->>'budget')::bigint
        or active_count > (p_state->>'concurrency_limit')::bigint then
        raise exception 'Principal budget or concurrency exceeded';
    end if;
    for entry in select key,value from jsonb_each(coalesce(old_state->'consents','{}')) loop
        if (entry.value - 'used') is distinct from ((p_state->'consents'->entry.key) - 'used')
            or (entry.value->'used' = 'true'::jsonb
                and p_state->'consents'->entry.key->'used' is distinct from 'true'::jsonb) then
            raise exception 'Consent terms and quoted evidence are immutable';
        end if;
    end loop;
    for entry in select key,value from jsonb_each(coalesce(p_state->'executions','{}')) loop
        if entry.value->>'principal' is distinct from p_principal
            or (entry.value->>'reserved')::bigint <= 0
            or entry.value->>'state' not in ('RESERVED','CALL_STARTED','UNKNOWN','GENERATED') then
            raise exception 'Invalid principal execution';
        end if;
    end loop;
    for entry in select key,value from jsonb_each(coalesce(old_state->'executions','{}')) loop
        if not (p_state->'executions' ? entry.key)
            or entry.value->'snapshot' is distinct from p_state->'executions'->entry.key->'snapshot'
            or entry.value->'snapshot_sha256' is distinct from p_state->'executions'->entry.key->'snapshot_sha256'
            or entry.value->'quote_sha256' is distinct from p_state->'executions'->entry.key->'quote_sha256'
            or (entry.value ? 'dispatch_evidence' and entry.value->'dispatch_evidence'
                is distinct from p_state->'executions'->entry.key->'dispatch_evidence')
            or entry.value->'reserved' is distinct from p_state->'executions'->entry.key->'reserved'
            or entry.value->'principal' is distinct from p_state->'executions'->entry.key->'principal'
            or entry.value->'consent_id' is distinct from p_state->'executions'->entry.key->'consent_id' then
            raise exception 'Execution snapshot is immutable';
        end if;
        if (entry.value->>'state' in ('UNKNOWN','GENERATED')
            and entry.value->>'state' is distinct from p_state->'executions'->entry.key->>'state')
            or (entry.value->>'state' = 'CALL_STARTED'
                and p_state->'executions'->entry.key->>'state' = 'RESERVED') then
            raise exception 'Execution replay forbidden';
        end if;
    end loop;
    update public.byop_ledgers set state=p_state, revision=revision+1, updated_at=now()
        where principal=p_principal and revision=p_revision;
    return found;
end;
$$;
revoke all on function public.byop_ledger_cas(text,bigint,jsonb) from public,anon,authenticated;
grant execute on function public.byop_ledger_cas(text,bigint,jsonb) to service_role;
commit;
