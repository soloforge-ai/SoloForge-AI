-- P0-B4 preparation only. DO NOT APPLY without separate approval.
-- Service-only durable evidence registry, grants, replay claims and append-only audit.
create table public.qa_reviewer_grants (
  grant_id uuid primary key default gen_random_uuid(),
  principal_id text not null check (length(principal_id) between 1 and 128),
  job_id text not null check (length(job_id) between 1 and 128),
  revision_id text not null check (length(revision_id) between 1 and 128),
  allowed_stages text[] not null check (cardinality(allowed_stages) between 1 and 6),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  check (revoked_at is null or revoked_at >= created_at)
);
create table public.qa_trusted_evidence (
  evidence_id text primary key check (length(evidence_id) between 1 and 128),
  job_id text not null check (length(job_id) between 1 and 128),
  stage text not null check (stage in ('CONTENT','GROUNDING','VISUAL','AUDIO','VIDEO_RENDER','FINAL_QA')),
  revision_id text not null check (length(revision_id) between 1 and 128),
  principal_id text not null check (length(principal_id) between 1 and 128),
  grant_id uuid not null references public.qa_reviewer_grants(grant_id),
  input_sha256 text not null check (input_sha256 ~ '^[0-9a-f]{64}$'),
  output_sha256 text not null check (output_sha256 ~ '^[0-9a-f]{64}$'),
  input_artifact_ref text not null check (length(input_artifact_ref) > 0),
  output_artifact_ref text not null check (length(output_artifact_ref) > 0),
  key_id text not null check (length(key_id) between 1 and 128),
  signature text not null check (signature ~ '^[0-9a-f]{64}$'),
  issued_at timestamptz not null default now(),
  unique(job_id,stage,revision_id,evidence_id)
);
create table public.qa_evidence_replay_claims (
  evidence_id text primary key references public.qa_trusted_evidence(evidence_id),
  claim_id uuid not null unique,
  claimed_at timestamptz not null default now()
);
create table public.qa_evidence_audit (
  id bigint generated always as identity primary key,
  evidence_id text not null,
  claim_id uuid,
  event_type text not null check (event_type in ('ISSUED','CLAIMED','REVOKED')),
  occurred_at timestamptz not null default now(),
  detail jsonb not null default '{}'::jsonb
);
create index qa_grants_lookup_idx on public.qa_reviewer_grants(principal_id,job_id,revision_id);
create index qa_evidence_job_idx on public.qa_trusted_evidence(job_id,stage,revision_id);
create index qa_audit_evidence_idx on public.qa_evidence_audit(evidence_id,id);
alter table public.qa_reviewer_grants enable row level security;
alter table public.qa_trusted_evidence enable row level security;
alter table public.qa_evidence_replay_claims enable row level security;
alter table public.qa_evidence_audit enable row level security;
revoke all on public.qa_reviewer_grants, public.qa_trusted_evidence,
  public.qa_evidence_replay_claims, public.qa_evidence_audit from public, anon, authenticated;
revoke all on public.qa_reviewer_grants, public.qa_trusted_evidence,
  public.qa_evidence_replay_claims, public.qa_evidence_audit from service_role;
revoke all on sequence public.qa_evidence_audit_id_seq from public, anon, authenticated, service_role;
-- Fail-closed: no direct table DML, even for service_role. Only controlled RPCs below.
create function public.qa_claim_verified_evidence(
  p_evidence_id text, p_claim_id uuid, p_job_id text, p_revision_id text,
  p_stage text, p_principal_id text
) returns boolean language plpgsql security definer set search_path = ''
as $$
declare v_e public.qa_trusted_evidence%rowtype;
begin
  if p_claim_id is null or p_evidence_id is null or p_job_id is null
     or p_revision_id is null or p_stage is null or p_principal_id is null then
    return false;
  end if;
  -- Lock grant before checking revocation. Revocation must use same row lock.
  select e.* into v_e
  from public.qa_trusted_evidence e
  where e.evidence_id = p_evidence_id and e.job_id = p_job_id
    and e.revision_id = p_revision_id and e.stage = p_stage
    and e.principal_id = p_principal_id;
  if not found then return false; end if;
  perform 1 from public.qa_reviewer_grants g
  where g.grant_id = v_e.grant_id and g.principal_id = v_e.principal_id
    and g.job_id = v_e.job_id and g.revision_id = v_e.revision_id
    and v_e.stage = any(g.allowed_stages)
    and g.revoked_at is null and g.expires_at > now()
  for update;
  if not found then return false; end if;
  -- The caller MUST cryptographically verify the evidence and artifact bytes
  -- against trusted server state before calling this RPC. This RPC cannot do so.
  insert into public.qa_evidence_replay_claims(evidence_id,claim_id)
  values (p_evidence_id,p_claim_id) on conflict do nothing;
  if not found then return false; end if;
  insert into public.qa_evidence_audit(evidence_id,claim_id,event_type)
  values (p_evidence_id,p_claim_id,'CLAIMED');
  return true;
end $$;
create function public.qa_revoke_reviewer_grant(p_grant_id uuid)
returns boolean language plpgsql security definer set search_path = ''
as $$
declare v_id uuid;
begin
  update public.qa_reviewer_grants
  set revoked_at = now()
  where grant_id = p_grant_id and revoked_at is null
  returning grant_id into v_id;
  if v_id is null then return false; end if;
  insert into public.qa_evidence_audit(evidence_id,event_type,detail)
  values (v_id::text,'REVOKED',jsonb_build_object('grant_id',v_id));
  return true;
end $$;
revoke all on function public.qa_claim_verified_evidence(text,uuid,text,text,text,text) from public,anon,authenticated;
revoke all on function public.qa_revoke_reviewer_grant(uuid) from public,anon,authenticated;
grant execute on function public.qa_claim_verified_evidence(text,uuid,text,text,text,text) to service_role;
grant execute on function public.qa_revoke_reviewer_grant(uuid) to service_role;
-- Grant creation and evidence issuance intentionally have NO exposed RPC yet:
-- secure identity/key custody, trusted immutable storage and issuance must be built
-- and audited before any live registration is possible.
