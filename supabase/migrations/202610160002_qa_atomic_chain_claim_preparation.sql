-- P0-B4 additive preparation. DO NOT APPLY WITHOUT SEPARATE APPROVAL.
-- No execute grant to service_role/anon/authenticated: trusted gateway not provisioned.
-- No runtime caller can claim an entire chain using this migration alone.
create table public.qa_chain_claims (
  chain_claim_id uuid primary key,
  job_id text not null,
  revision_id text not null,
  route text not null check (route in ('IMAGE','VIDEO')),
  created_at timestamptz not null default now()
);
create table public.qa_chain_members (
  evidence_id text primary key references public.qa_trusted_evidence(evidence_id),
  chain_claim_id uuid not null references public.qa_chain_claims(chain_claim_id),
  ordinal integer not null check (ordinal >= 1),
  unique(chain_claim_id, ordinal)
);
alter table public.qa_chain_claims enable row level security;
alter table public.qa_chain_members enable row level security;
revoke all on public.qa_chain_claims, public.qa_chain_members from public,anon,authenticated,service_role;
-- A claim is transactionally all-or-nothing; this RPC does NOT perform
-- cryptographic verification and MUST NOT be exposed until trusted gateway
-- authorization, live snapshot locking and immutable artifact revalidation exist.
create function public.qa_claim_verified_chain(
 p_chain_claim_id uuid, p_job_id text, p_revision_id text,
 p_route text, p_evidence_ids text[]
) returns boolean language plpgsql security definer set search_path = ''
as $$
declare v_stages text[]; v_id text; v_e public.qa_trusted_evidence%rowtype;
declare v_ordinal integer := 0;
begin
  if p_chain_claim_id is null or p_job_id is null or p_revision_id is null
     or p_route not in ('IMAGE','VIDEO') or p_evidence_ids is null then
    return false;
  end if;
  v_stages := case p_route
    when 'IMAGE' then array['CONTENT','GROUNDING','VISUAL']
    when 'VIDEO' then array['CONTENT','GROUNDING','VISUAL','AUDIO','VIDEO_RENDER']
    else null end;
  if cardinality(p_evidence_ids) != cardinality(v_stages)
     or exists(select 1 from unnest(p_evidence_ids) as x where x is null)
     or (select count(distinct x) from unnest(p_evidence_ids) as x)
          != cardinality(v_stages) then
    return false;
  end if;
  -- Deterministic lock order prevents cross-chain grant lock inversion.
  perform 1 from public.qa_reviewer_grants g
    where g.grant_id in (
      select e.grant_id from public.qa_trusted_evidence e
      where e.evidence_id = any(p_evidence_ids))
    order by g.grant_id for update;
  -- Recheck all grants after locks; fail atomically on revocation/expiry.
  for v_id in select unnest(p_evidence_ids) loop
    v_ordinal := v_ordinal + 1;
    select e.* into v_e from public.qa_trusted_evidence e
      join public.qa_reviewer_grants g on g.grant_id=e.grant_id
      where e.evidence_id=v_id and e.job_id=p_job_id
        and e.revision_id=p_revision_id and e.stage=v_stages[v_ordinal]
        and g.principal_id=e.principal_id and g.job_id=e.job_id
        and g.revision_id=e.revision_id and e.stage=any(g.allowed_stages)
        and g.revoked_at is null and g.expires_at > clock_timestamp();
    if not found then return false; end if;
  end loop;
  -- No previous per-evidence or chain claim is allowed.
  if exists(select 1 from public.qa_evidence_replay_claims
            where evidence_id=any(p_evidence_ids)) then return false; end if;
  insert into public.qa_chain_claims(chain_claim_id,job_id,revision_id,route)
    values(p_chain_claim_id,p_job_id,p_revision_id,p_route)
    on conflict do nothing;
  if not found then return false; end if;
  v_ordinal := 0;
  foreach v_id in array p_evidence_ids loop
    v_ordinal := v_ordinal + 1;
    insert into public.qa_chain_members(evidence_id,chain_claim_id,ordinal)
      values(v_id,p_chain_claim_id,v_ordinal) on conflict do nothing;
    if not found then
      raise exception 'qa_chain_replay_conflict' using errcode='23505';
    end if;
    insert into public.qa_evidence_replay_claims(evidence_id,claim_id)
      values(v_id,gen_random_uuid()) on conflict do nothing;
    if not found then
      raise exception 'qa_chain_replay_conflict' using errcode='23505';
    end if;
    insert into public.qa_evidence_audit(evidence_id,claim_id,event_type,detail)
      values(v_id,p_chain_claim_id,'CLAIMED',
             jsonb_build_object('route',p_route,'ordinal',v_ordinal));
  end loop;
  return true;
end $$;
revoke all on function public.qa_claim_verified_chain(uuid,text,text,text,text[])
  from public,anon,authenticated,service_role;
-- Intentionally no GRANT EXECUTE. PostgreSQL owner-only fixture testing is
-- permitted on disposable CI. Production use is blocked by design.
