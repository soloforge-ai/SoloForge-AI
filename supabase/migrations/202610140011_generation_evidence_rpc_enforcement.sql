-- Trusted evidence enforcement. No issuer or provider calls in this migration.
-- Applied after synthetic legacy functional tests until trusted issuer exists.
begin;
grant usage on schema generation_evidence to service_role;
grant execute on function generation_evidence.check_result(uuid,uuid,uuid,text,text,text,numeric) to service_role;
create or replace function public.generation_record_verified_result(
 p_request uuid,p_owner uuid,p_session text,p_outcome text,p_evidence_ref text,
 p_observed numeric,p_bucket text default null,p_object_key text default null,
 p_version text default null,p_sha text default null
) returns boolean language plpgsql security definer set search_path='' as $$
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
 if p_outcome in ('SUCCEEDED','FAILED_CONFIRMED') and not generation_evidence.check_result(
   e.id,r.id,p_owner,p_session,p_evidence_ref,p_outcome,p_observed)
 then raise exception 'trusted provider result evidence missing or expired' using errcode='42501'; end if;
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

create or replace function public.generation_settle_execution(
 p_execution uuid,p_owner uuid,p_session text,p_actual numeric,p_evidence_ref text
) returns boolean language plpgsql security definer set search_path = '' as $$
declare e public.generation_executions%rowtype; b public.generation_budget_accounts%rowtype;
 v_settled boolean; v_released numeric;
begin
 if (session_user <> 'service_role' and current_setting('role') <> 'service_role') then raise exception 'service role required' using errcode='42501'; end if;
 if p_actual is null or p_actual < 0 or p_actual >= 'Infinity'::numeric
 or nullif(btrim(p_evidence_ref),'') is null then raise exception 'invalid settlement'; end if;
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.owner_user_id is distinct from p_owner or e.pollinations_session_id is distinct from p_session
 then raise exception 'owner or session mismatch' using errcode='42501'; end if;
 if e.state not in ('CALL_STARTED','UNKNOWN_RECONCILE','SUCCEEDED','FAILED_CONFIRMED') then
  raise exception 'execution not ready for verified settlement'; end if;
 if exists(select 1 from public.generation_requests where execution_id=e.id and state not in ('SUCCEEDED','FAILED_CONFIRMED'))
 then raise exception 'incomplete or ambiguous slide'; end if;
 if p_actual > e.reserved_pollen then raise exception 'actual exceeds reserved'; end if;
 -- A caller cannot settle a different amount than the immutable per-slide
 -- observations. Provider-origin verification remains a separate release gate.
 if (select coalesce(sum(observed_pollen),0) from public.generation_requests
     where execution_id=e.id) is distinct from p_actual
 then raise exception 'settlement amount does not match observed slide total'; end if;
 if exists (
   select 1 from public.generation_requests r
   where r.execution_id=e.id and not exists (
     select 1 from public.generation_events ev
     where ev.execution_id=e.id and ev.request_id=r.id
       and ev.event_type=r.state
       and (ev.safe_detail->>'observed_pollen')::numeric=r.observed_pollen
   )
 ) then raise exception 'missing matching immutable result evidence'; end if;
 if exists (
   select 1 from public.generation_requests r
   where r.execution_id=e.id and not exists (
     select 1 from generation_evidence.verified_results v
     where v.execution_id=e.id and v.request_id=r.id
       and v.owner_user_id=p_owner and v.pollinations_session_id=p_session
       and v.outcome=r.state and v.observed_pollen=r.observed_pollen
       and v.verified_at<=clock_timestamp() and v.expires_at>clock_timestamp()
       and exists (select 1 from public.generation_events ev
         where ev.execution_id=e.id and ev.request_id=r.id
           and ev.event_type=r.state and ev.safe_detail->>'evidence_ref'=v.evidence_ref)
   )
 ) then raise exception 'trusted settlement evidence missing or expired' using errcode='42501'; end if;
 select * into b from public.generation_budget_accounts where id=e.budget_account_id for update;
 if b.owner_user_id <> p_owner or b.pollinations_session_id <> p_session
 then raise exception 'wallet mismatch' using errcode='42501'; end if;
 select exists(select 1 from public.generation_budget_ledger where execution_id=e.id and entry_kind='SETTLE')
 into v_settled;
 if v_settled then
  if e.observed_pollen is distinct from p_actual then raise exception 'settlement replay conflict'; end if;
  return true;
 end if;
 if e.state in ('SUCCEEDED','FAILED_CONFIRMED') then raise exception 'terminal state without settlement ledger'; end if;
 if b.reserved_pollen < e.reserved_pollen then raise exception 'reservation drift'; end if;
 update public.generation_budget_accounts
 set reserved_pollen=reserved_pollen-e.reserved_pollen,
 spent_pollen=spent_pollen+p_actual,revision=revision+1 where id=b.id;
 insert into public.generation_budget_ledger
  (execution_id,budget_account_id,owner_user_id,pollinations_session_id,entry_key,entry_kind,amount_pollen,evidence_ref)
 values(e.id,b.id,p_owner,p_session,e.execution_key||':settle','SETTLE',p_actual,p_evidence_ref);
 v_released:=e.reserved_pollen-p_actual;
 if v_released>0 then
  insert into public.generation_budget_ledger
   (execution_id,budget_account_id,owner_user_id,pollinations_session_id,entry_key,entry_kind,amount_pollen,evidence_ref)
  values(e.id,b.id,p_owner,p_session,e.execution_key||':release','RELEASE_AFTER_VERIFICATION',v_released,p_evidence_ref);
 end if;
 insert into public.generation_events
  (execution_id,budget_account_id,owner_user_id,pollinations_session_id,event_key,event_type,safe_detail)
 values(e.id,b.id,p_owner,p_session,e.execution_key||':budget-settled','BUDGET_SETTLED',
        jsonb_build_object('evidence_ref',p_evidence_ref,'actual_pollen',p_actual));
 if v_released>0 then
  insert into public.generation_events
   (execution_id,budget_account_id,owner_user_id,pollinations_session_id,event_key,event_type,safe_detail)
  values(e.id,b.id,p_owner,p_session,e.execution_key||':budget-released','BUDGET_RELEASED',
         jsonb_build_object('evidence_ref',p_evidence_ref,'released_pollen',v_released));
 end if;
 update public.generation_executions set state=(case when exists(select 1 from public.generation_requests where execution_id=e.id and state='FAILED_CONFIRMED') then 'FAILED_CONFIRMED' else 'SUCCEEDED' end),observed_pollen=p_actual,settled_at=clock_timestamp(),revision=revision+1
 where id=e.id;
 return true;
end $$;

create or replace function public.generation_resume_after_reconciliation(
 p_execution uuid,p_owner uuid,p_session text,p_evidence_ref text
) returns boolean language plpgsql security definer set search_path='' as $$
declare e public.generation_executions%rowtype;
begin
 if session_user <> 'service_role' and current_setting('role') <> 'service_role'
 then raise exception 'service role required' using errcode='42501'; end if;
 if nullif(btrim(p_evidence_ref),'') is null then raise exception 'evidence required'; end if;
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.owner_user_id is distinct from p_owner
 or e.pollinations_session_id is distinct from p_session
 then raise exception 'owner mismatch' using errcode='42501'; end if;
 if e.state <> 'UNKNOWN_RECONCILE' then raise exception 'not in reconciliation'; end if;
 if exists(select 1 from public.generation_requests where execution_id=e.id
           and state in ('UNKNOWN_RECONCILE','CALL_STARTED','FAILED_CONFIRMED'))
 then raise exception 'unresolved or failed slide; no resume'; end if;
 if not exists(select 1 from public.generation_requests r
   join public.generation_events ev on ev.request_id=r.id and ev.execution_id=e.id
   where r.execution_id=e.id and r.state='SUCCEEDED' and ev.event_type='RECONCILED'
   and ev.safe_detail->>'evidence_ref'=p_evidence_ref)
 then raise exception 'matching immutable reconciliation evidence missing'; end if;
 if not exists (
   select 1 from public.generation_requests r
   where r.execution_id=e.id and r.state='SUCCEEDED'
     and generation_evidence.check_result(e.id,r.id,p_owner,p_session,
         p_evidence_ref,'SUCCEEDED',r.observed_pollen)
     and exists (select 1 from public.generation_events ev
       where ev.execution_id=e.id and ev.request_id=r.id
         and ev.event_type='RECONCILED'
         and ev.safe_detail->>'evidence_ref'=p_evidence_ref)
 ) then raise exception 'trusted recovery evidence missing or expired' using errcode='42501'; end if;
 if not exists(select 1 from public.generation_requests where execution_id=e.id and state='PENDING')
 then raise exception 'nothing to resume; settle instead'; end if;
 -- Only the earliest pending slide is eligible to resume. Later pending slides
 -- must remain pending and must not block recovery of the immediate next slide.
 if exists(
   select 1 from public.generation_requests earlier
   where earlier.execution_id=e.id
     and earlier.slide_ordinal < (
       select min(next_slide.slide_ordinal)
       from public.generation_requests next_slide
       where next_slide.execution_id=e.id and next_slide.state='PENDING'
     )
     and earlier.state <> 'SUCCEEDED'
 )
 then raise exception 'sequential slide fence failed'; end if;
 update public.generation_executions set state='CALL_STARTED',revision=revision+1 where id=e.id;
 return true;
end $$;

commit;
