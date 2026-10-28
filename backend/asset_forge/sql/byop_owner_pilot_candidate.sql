-- Local additive candidate only, after byop_v1_candidate + byop_v1_integration.
-- No runtime/client issuance. An independently authorized administrator must
-- provision one exact permit. Applying this file alone activates no provider I/O.
begin;
create table public.byop_owner_pilot_permits (
    execution_id uuid primary key,
    principal text not null references public.byop_ledgers(principal)
        check (principal ~ '^owner:[0-9a-f-]{36}$'),
    terms jsonb not null check (terms->>'principal' = principal
        and terms->>'execution_id' = execution_id::text
        and terms->'manual_reconciliation_accepted' = 'true'::jsonb),
    created_at timestamptz not null default now(),
    consumed_at timestamptz
);
alter table public.byop_owner_pilot_permits enable row level security;
revoke all on public.byop_owner_pilot_permits from public,anon,authenticated,service_role;
grant select, update(consumed_at) on public.byop_owner_pilot_permits to service_role;

create function public.byop_pilot_permit_immutable() returns trigger
language plpgsql set search_path='' as $$
begin
    if (to_jsonb(old)-'consumed_at') is distinct from (to_jsonb(new)-'consumed_at')
        or old.consumed_at is not null or new.consumed_at is null then
        raise exception 'Pilot permit immutable or consumed';
    end if;
    return new;
end;
$$;
create trigger byop_pilot_permit_immutable before update on public.byop_owner_pilot_permits
for each row execute function public.byop_pilot_permit_immutable();

create function public.byop_claim_owner_pilot(p_principal text,p_execution uuid,
    p_snapshot_hash text,p_quote_hash text,p_evidence jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare l public.byop_ledgers; p public.byop_owner_pilot_permits;
    e jsonb; c jsonb; expected jsonb; claimed jsonb; held numeric;
begin
    if p_principal is null or p_principal !~ '^owner:[0-9a-f-]{36}$' then
        raise exception 'Owner pilot only';
    end if;
    perform public.byop_assert_principal(p_principal);
    -- Same lock order as the retained ledger/credential/job claim. No second
    -- wallet or execution store: permit consumption and CALL_STARTED commit
    -- together. Any exception, including a late expiry, rolls back both.
    select * into l from public.byop_ledgers where principal=p_principal for update;
    select * into p from public.byop_owner_pilot_permits
        where execution_id=p_execution and principal=p_principal for update;
    if not found or p.consumed_at is not null then raise exception 'Pilot permit unavailable'; end if;
    e:=l.state->'executions'->p_execution::text;
    c:=l.state->'consents'->(e->>'consent_id');
    if e is null or c is null or e->>'state' is distinct from 'RESERVED'
        or e->>'principal' is distinct from p_principal
        or c->>'principal' is distinct from p_principal
        or e->>'snapshot_sha256' is distinct from p_snapshot_hash
        or e->>'quote_sha256' is distinct from p_quote_hash
        or c->'snapshot' is distinct from e->'snapshot'
        or c->'quote'->'includes_all_charges' is distinct from 'true'::jsonb then
        raise exception 'Pilot execution or quote mismatch';
    end if;
    expected:=jsonb_build_object('principal',p_principal,'execution_id',p_execution::text,
        'credential_id',e->'snapshot'->>'credential_id','job_id',e->'snapshot'->>'job_id',
        'model',e->'snapshot'->>'model','consent_id',e->>'consent_id',
        'snapshot_sha256',p_snapshot_hash,'quote_sha256',p_quote_hash,
        'maximum_micro_pollen',c->'maximum');
    if not p.terms @> expected
        or p.terms->'manual_reconciliation_accepted' is distinct from 'true'::jsonb
        or jsonb_typeof(p.terms->'expires_at') is distinct from 'number'
        or (p.terms->>'expires_at')::numeric <= extract(epoch from clock_timestamp())
        or (p.terms->>'expires_at')::numeric > least((e->>'expires_at')::numeric,(c->>'expires_at')::numeric)
        or (c->>'maximum')::bigint < (e->>'reserved')::bigint then
        raise exception 'Pilot permit expired or binding mismatch';
    end if;
    select coalesce(sum((value->>'reserved')::numeric),0) into held
        from jsonb_each(coalesce(l.state->'executions','{}'))
        where value->>'state' in ('RESERVED','CALL_STARTED','UNKNOWN','GENERATED');
    if p_evidence is null
        or (p_evidence-'available_micro_pollen'-'observed_at'-'expires_at') is distinct from
           ((c->'quote')-'available_micro_pollen'-'observed_at'-'expires_at')
        or jsonb_typeof(p_evidence->'observed_at') is distinct from 'number'
        or jsonb_typeof(p_evidence->'expires_at') is distinct from 'number'
        or jsonb_typeof(p_evidence->'available_micro_pollen') is distinct from 'number'
        or not ((p_evidence->>'observed_at')::numeric <= extract(epoch from clock_timestamp())
            and (p_evidence->>'observed_at')::numeric > extract(epoch from clock_timestamp())-30)
        or (p_evidence->>'expires_at')::numeric <= extract(epoch from clock_timestamp())
        or (p_evidence->>'available_micro_pollen')::numeric < held then
        raise exception 'Fresh evidence cannot cover aggregate reservations';
    end if;
    claimed:=public.byop_claim_execution(p_principal,p_execution,p_snapshot_hash);
    if (p.terms->>'expires_at')::numeric <= extract(epoch from clock_timestamp()) then
        raise exception 'Pilot permit expired during claim';
    end if;
    -- Freeze the trusted dispatch observation alongside the retained snapshot.
    select * into l from public.byop_ledgers where principal=p_principal;
    claimed:=claimed||jsonb_build_object('dispatch_evidence',p_evidence);
    if not public.byop_ledger_cas(p_principal,l.revision,
        jsonb_set(l.state,array['executions',p_execution::text],claimed)) then
        raise exception 'Dispatch evidence persistence failed';
    end if;
    update public.byop_owner_pilot_permits set consumed_at=clock_timestamp() where execution_id=p_execution;
    return jsonb_build_object('execution',claimed,'permit',p.terms);
end;
$$;
revoke all on function public.byop_pilot_permit_immutable() from public,anon,authenticated,service_role;
revoke all on function public.byop_claim_owner_pilot(text,uuid,text,text,jsonb) from public,anon,authenticated;
grant execute on function public.byop_claim_owner_pilot(text,uuid,text,text,jsonb) to service_role;
commit;
