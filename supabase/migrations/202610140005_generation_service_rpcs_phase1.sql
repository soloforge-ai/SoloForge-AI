-- P2-B1 service-only, fail-closed reservation and reconciliation primitives.
-- NO provider execution; wallet identity/authorization must be attested upstream.
-- Only callable as the actual database service_role, never via user JWT.
create or replace function public.generation_reserve_execution(
 p_approval uuid, p_owner uuid, p_session text, p_execution_key text
) returns uuid language plpgsql security invoker set search_path = '' as $$
declare a public.generation_approvals%rowtype; b public.generation_budget_accounts%rowtype;
 e public.generation_executions%rowtype; v_id uuid; v_slide jsonb; i integer;
begin
 if current_user <> 'service_role' then raise exception 'service role required' using errcode='42501'; end if;
 if nullif(btrim(p_execution_key),'') is null then raise exception 'empty key'; end if;
 select * into a from public.generation_approvals where id=p_approval for update;
 if not found or a.owner_user_id is distinct from p_owner
 or a.pollinations_session_id is distinct from p_session
 or a.state <> 'APPROVED' or a.revoked_at is not null
 or a.expires_at <= clock_timestamp() or a.quote_expires_at <= clock_timestamp()
 then raise exception 'approval unauthorized or expired' using errcode='42501'; end if;
 select * into b from public.generation_budget_accounts where id=a.budget_account_id for update;
 if not found or b.owner_user_id <> p_owner or b.pollinations_session_id <> p_session
 or b.allocation_state <> 'ALLOCATED' or b.allocation_verified_at is null
 or b.owner_session_verified_at is null or b.allocation_ref is null
 then raise exception 'wallet not attested or allocated' using errcode='42501'; end if;
 select * into e from public.generation_executions where approval_id=a.id;
 if found then
  if e.execution_key <> p_execution_key then raise exception 'approval already claimed'; end if;
  return e.id;
 end if;
 if exists(select 1 from public.generation_executions where execution_key=p_execution_key)
 then raise exception 'execution key reused'; end if;
 if b.allocated_pollen-b.reserved_pollen-b.spent_pollen < a.max_pollen
 then raise exception 'insufficient wallet allocation'; end if;
 update public.generation_budget_accounts
 set reserved_pollen=reserved_pollen+a.max_pollen,revision=revision+1 where id=b.id;
 insert into public.generation_executions
  (approval_id,execution_key,budget_account_id,owner_user_id,pollinations_session_id,
   snapshot_digest,snapshot_json,reserved_pollen)
 values (a.id,p_execution_key,b.id,p_owner,p_session,a.snapshot_digest,a.snapshot_json,a.max_pollen)
 returning id into v_id;
 for i in 1..4 loop
  v_slide:=a.snapshot_json->'slides'->(i-1);
  insert into public.generation_requests
   (execution_id,budget_account_id,owner_user_id,pollinations_session_id,
    slide_ordinal,request_key,request_snapshot,max_pollen)
  values (v_id,b.id,p_owner,p_session,i,p_execution_key||':slide:'||i,v_slide,a.max_pollen);
 end loop;
 insert into public.generation_budget_ledger
  (execution_id,budget_account_id,owner_user_id,pollinations_session_id,entry_key,entry_kind,amount_pollen)
 values(v_id,b.id,p_owner,p_session,p_execution_key||':reserve','RESERVE',a.max_pollen);
 update public.generation_approvals set state='CLAIMED',revision=revision+1 where id=a.id;
 return v_id;
end $$;

-- Only after verified external reconciliation, with explicit evidence reference.
-- No automatic release for UNKNOWN_RECONCILE or CALL_STARTED.
create or replace function public.generation_settle_execution(
 p_execution uuid,p_owner uuid,p_session text,p_actual numeric,p_evidence_ref text
) returns boolean language plpgsql security invoker set search_path = '' as $$
declare e public.generation_executions%rowtype; b public.generation_budget_accounts%rowtype;
 v_settled boolean; v_released numeric;
begin
 if current_user <> 'service_role' then raise exception 'service role required' using errcode='42501'; end if;
 if p_actual is null or p_actual < 0 or p_actual >= 'Infinity'::numeric
 or nullif(btrim(p_evidence_ref),'') is null then raise exception 'invalid settlement'; end if;
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.owner_user_id is distinct from p_owner or e.pollinations_session_id is distinct from p_session
 then raise exception 'owner or session mismatch' using errcode='42501'; end if;
 if e.state not in ('SUCCEEDED','FAILED_CONFIRMED') then
  raise exception 'unreconciled provider result; settlement prohibited'; end if;
 if exists(select 1 from public.generation_requests where execution_id=e.id and state not in ('SUCCEEDED','FAILED_CONFIRMED'))
 then raise exception 'incomplete or ambiguous slide'; end if;
 if p_actual > e.reserved_pollen then raise exception 'actual exceeds reserved'; end if;
 select * into b from public.generation_budget_accounts where id=e.budget_account_id for update;
 if b.owner_user_id <> p_owner or b.pollinations_session_id <> p_session
 then raise exception 'wallet mismatch' using errcode='42501'; end if;
 select exists(select 1 from public.generation_budget_ledger where execution_id=e.id and entry_kind='SETTLE')
 into v_settled;
 if v_settled then
  if e.observed_pollen is distinct from p_actual then raise exception 'settlement replay conflict'; end if;
  return true;
 end if;
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
 update public.generation_executions set observed_pollen=p_actual,settled_at=clock_timestamp(),revision=revision+1
 where id=e.id;
 return true;
end $$;
revoke all on function public.generation_reserve_execution(uuid,uuid,text,text) from public,anon,authenticated;
revoke all on function public.generation_settle_execution(uuid,uuid,text,numeric,text) from public,anon,authenticated;
grant execute on function public.generation_reserve_execution(uuid,uuid,text,text) to service_role;
grant execute on function public.generation_settle_execution(uuid,uuid,text,numeric,text) to service_role;
