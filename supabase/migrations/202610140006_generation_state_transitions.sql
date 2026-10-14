-- Manual-only state transitions. This does not dispatch a provider call.
-- Caller must validate authorization and provider evidence before invoking.
create or replace function public.generation_mark_call_started(
 p_request uuid,p_owner uuid,p_session text
) returns boolean language plpgsql security invoker set search_path='' as $$
declare e public.generation_executions%rowtype; r public.generation_requests%rowtype;
begin
 if (session_user <> 'service_role' and current_setting('role') <> 'service_role') then raise exception 'service role required' using errcode='42501'; end if;
 select * into r from public.generation_requests where id=p_request;
 if not found then raise exception 'unknown request'; end if;
 select * into e from public.generation_executions where id=r.execution_id for update;
 if e.owner_user_id is distinct from p_owner or e.pollinations_session_id is distinct from p_session
 then raise exception 'owner mismatch' using errcode='42501'; end if;
 select * into r from public.generation_requests where id=p_request for update;
 if r.state <> 'PENDING' then return false; end if;
 if e.state not in ('CLAIMED','CALL_STARTED') then raise exception 'execution terminal or ambiguous'; end if;
 if exists(select 1 from public.generation_requests where execution_id=e.id and slide_ordinal<r.slide_ordinal and state<>'SUCCEEDED')
 or exists(select 1 from public.generation_requests where execution_id=e.id and slide_ordinal<>r.slide_ordinal and state in ('CALL_STARTED','UNKNOWN_RECONCILE'))
 then return false; end if;
 update public.generation_requests set state='CALL_STARTED',call_started_at=clock_timestamp() where id=r.id;
 if e.state='CLAIMED' then
  update public.generation_executions set state='CALL_STARTED',call_started_at=clock_timestamp(),revision=revision+1 where id=e.id;
 end if;
 return true;
end $$;

-- Provider results must be independently verified before invoking; ambiguous outcomes
-- are fenced until explicit reconciliation. No retry or release is initiated here.
create or replace function public.generation_record_verified_result(
 p_request uuid,p_owner uuid,p_session text,p_outcome text,p_evidence_ref text,
 p_observed numeric,p_bucket text default null,p_object_key text default null,
 p_version text default null,p_sha text default null
) returns boolean language plpgsql security invoker set search_path='' as $$
declare e public.generation_executions%rowtype; r public.generation_requests%rowtype;
begin
 if (session_user <> 'service_role' and current_setting('role') <> 'service_role') then raise exception 'service role required' using errcode='42501'; end if;
 if p_outcome not in ('SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_RECONCILE')
 or nullif(btrim(p_evidence_ref),'') is null
 or p_observed is null or p_observed < 0 then raise exception 'invalid result evidence'; end if;
 if p_outcome='SUCCEEDED' and (nullif(btrim(p_bucket),'') is null or nullif(btrim(p_object_key),'') is null
 or nullif(btrim(p_version),'') is null or p_sha !~ '^[0-9a-f]{64}$')
 then raise exception 'immutable output reference required'; end if;
 select * into r from public.generation_requests where id=p_request;
 if not found then raise exception 'unknown request'; end if;
 select * into e from public.generation_executions where id=r.execution_id for update;
 if e.owner_user_id is distinct from p_owner or e.pollinations_session_id is distinct from p_session
 then raise exception 'owner mismatch' using errcode='42501'; end if;
 select * into r from public.generation_requests where id=p_request for update;
 if r.state not in ('CALL_STARTED','UNKNOWN_RECONCILE') then raise exception 'result already terminal or never started'; end if;
 if r.state='UNKNOWN_RECONCILE' and p_outcome='UNKNOWN_RECONCILE' then return false; end if;
 update public.generation_requests
 set state=p_outcome,completed_at=case when p_outcome='UNKNOWN_RECONCILE' then null else clock_timestamp() end,
 observed_pollen=p_observed,
 output_bucket=case when p_outcome='SUCCEEDED' then p_bucket else null end,
 output_object_key=case when p_outcome='SUCCEEDED' then p_object_key else null end,
 output_object_version=case when p_outcome='SUCCEEDED' then p_version else null end,
 output_sha256=case when p_outcome='SUCCEEDED' then p_sha else null end
 where id=r.id;
 insert into public.generation_events
  (execution_id,budget_account_id,owner_user_id,pollinations_session_id,request_id,
   event_key,event_type,safe_detail)
 values(e.id,e.budget_account_id,p_owner,p_session,r.id,
  r.request_key||':result:'||p_outcome,p_outcome,
  jsonb_build_object('evidence_ref',p_evidence_ref,'observed_pollen',p_observed,
    'outcome',p_outcome,'output_sha256',case when p_outcome='SUCCEEDED' then p_sha else null end));
 if r.state='UNKNOWN_RECONCILE' and p_outcome<>'UNKNOWN_RECONCILE' then
  insert into public.generation_events
   (execution_id,budget_account_id,owner_user_id,pollinations_session_id,request_id,
    event_key,event_type,safe_detail)
  values(e.id,e.budget_account_id,p_owner,p_session,r.id,
    r.request_key||':reconciled','RECONCILED',
    jsonb_build_object('evidence_ref',p_evidence_ref,'outcome',p_outcome));
 end if;
 if p_outcome='UNKNOWN_RECONCILE' then
  update public.generation_executions set state='UNKNOWN_RECONCILE',revision=revision+1 where id=e.id;
 end if;
 return true;
end $$;
revoke all on function public.generation_mark_call_started(uuid,uuid,text) from public,anon,authenticated;
revoke all on function public.generation_record_verified_result(uuid,uuid,text,text,text,numeric,text,text,text,text) from public,anon,authenticated;
grant execute on function public.generation_mark_call_started(uuid,uuid,text) to service_role;
grant execute on function public.generation_record_verified_result(uuid,uuid,text,text,text,numeric,text,text,text,text) to service_role;
