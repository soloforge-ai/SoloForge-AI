-- P2-B1 offline evidence registry. NOT a provider verifier.
-- A separately audited issuer must validate provider evidence before any insert.
begin;
create schema if not exists generation_evidence;
revoke all on schema generation_evidence from public, anon, authenticated, service_role;
create table generation_evidence.verified_results (
 id uuid primary key default gen_random_uuid(),
 execution_id uuid not null references public.generation_executions(id) on delete restrict,
 request_id uuid not null references public.generation_requests(id) on delete restrict,
 owner_user_id uuid not null references auth.users(id) on delete restrict,
 pollinations_session_id text not null references public.pollinations_sessions(session_id) on delete restrict,
 provider_request_ref text not null check (length(btrim(provider_request_ref))>0),
 authorization_ref text not null check (length(btrim(authorization_ref))>0),
 evidence_ref text not null check (length(btrim(evidence_ref))>0),
 evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
 outcome text not null check (outcome in ('SUCCEEDED','FAILED_CONFIRMED')),
 observed_pollen numeric(20,8) not null check (observed_pollen>=0),
 issuer_id text not null check (length(btrim(issuer_id))>0),
 verified_at timestamptz not null,
 expires_at timestamptz not null check (expires_at>verified_at),
 unique (request_id, evidence_ref),
 unique (provider_request_ref)
);
create trigger verified_results_immutable before update or delete on generation_evidence.verified_results
 for each row execute function generation_internal.guard_immutable('');
alter table generation_evidence.verified_results enable row level security;
alter table generation_evidence.verified_results force row level security;
revoke all on generation_evidence.verified_results from public,anon,authenticated,service_role;
create or replace function generation_evidence.check_result(
 p_execution uuid,p_request uuid,p_owner uuid,p_session text,
 p_evidence_ref text,p_outcome text,p_observed numeric
) returns boolean language sql security definer set search_path='' as $$
 select exists (
  select 1 from generation_evidence.verified_results v
  where v.execution_id=p_execution and v.request_id=p_request
    and v.owner_user_id=p_owner and v.pollinations_session_id=p_session
    and v.evidence_ref=p_evidence_ref and v.outcome=p_outcome
    and v.observed_pollen=p_observed
    and v.verified_at<=clock_timestamp() and v.expires_at>clock_timestamp()
 )
$$;
revoke all on function generation_evidence.check_result(uuid,uuid,uuid,text,text,text,numeric)
 from public,anon,authenticated,service_role;
-- Deliberately no grant to service_role until caller enforcement and issuer are integrated.
commit;
