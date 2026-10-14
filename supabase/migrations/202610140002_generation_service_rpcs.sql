-- P2-B1 service-only state machine. Never calls an external provider.
-- All functions reject non-service JWT roles even when called through SECURITY DEFINER.
create or replace function public.generation_assert_service()
returns void language plpgsql security invoker set search_path = '' as $$
begin
 if coalesce(auth.role(),'') <> 'service_role' then
  raise exception 'generation service authorization required' using errcode='42501';
 end if;
end $$;

create or replace function public.generation_create_execution(
 p_owner uuid, p_approval uuid, p_idempotency text, p_snapshot jsonb
) returns uuid language plpgsql security definer set search_path = '' as $$
declare a public.generation_approvals%rowtype; b public.generation_budget_accounts%rowtype; v_id uuid;
begin
 perform public.generation_assert_service();
 if p_owner is null or nullif(btrim(p_idempotency),'') is null
   or jsonb_typeof(p_snapshot) <> 'object' then raise exception 'invalid execution input'; end if;
 select * into a from public.generation_approvals where id=p_approval;
 if not found or a.owner_user_id <> p_owner or a.expires_at <= now() then
  raise exception 'invalid or expired approval' using errcode='42501';
 end if;
 select * into b from public.generation_budget_accounts where id=a.budget_account_id;
 if not found or b.owner_user_id <> p_owner then raise exception 'wallet owner mismatch' using errcode='42501'; end if;
 insert into public.generation_executions(approval_id,budget_account_id,owner_user_id,idempotency_key,execution_snapshot)
 values (p_approval,a.budget_account_id,p_owner,p_idempotency,p_snapshot)
 on conflict (owner_user_id,idempotency_key) do nothing returning id into v_id;
 if v_id is null then
  select id into v_id from public.generation_executions
  where owner_user_id=p_owner and idempotency_key=p_idempotency
    and approval_id=p_approval and execution_snapshot=p_snapshot;
  if v_id is null then raise exception 'idempotency conflict'; end if;
 end if;
 return v_id;
end $$;

create or replace function public.generation_approve_execution(p_execution uuid, p_owner uuid)
returns boolean language plpgsql security definer set search_path = '' as $$
declare e public.generation_executions%rowtype; a public.generation_approvals%rowtype;
begin
 perform public.generation_assert_service();
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.owner_user_id <> p_owner then raise exception 'execution owner mismatch' using errcode='42501'; end if;
 select * into a from public.generation_approvals where id=e.approval_id;
 if a.owner_user_id <> p_owner or a.budget_account_id <> e.budget_account_id or a.expires_at <= now()
 then raise exception 'approval mismatch or expired' using errcode='42501'; end if;
 if e.state='APPROVED' then return true; end if;
 if e.state <> 'PENDING' then raise exception 'invalid approval transition'; end if;
 update public.generation_executions set state='APPROVED' where id=p_execution;
 return true;
end $$;

create or replace function public.generation_reserve_budget(
 p_execution uuid, p_request uuid, p_amount numeric, p_idempotency text
) returns uuid language plpgsql security definer set search_path = '' as $$
declare e public.generation_executions%rowtype; a public.generation_approvals%rowtype;
 b public.generation_budget_accounts%rowtype; r public.generation_requests%rowtype;
 v_total numeric; v_id uuid;
begin
 perform public.generation_assert_service();
 if p_amount is null or p_amount <= 0 or nullif(btrim(p_idempotency),'') is null then raise exception 'invalid reservation'; end if;
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.state not in ('APPROVED','RUNNING') then raise exception 'execution not approved'; end if;
 select * into a from public.generation_approvals where id=e.approval_id;
 if a.expires_at <= now() or a.owner_user_id <> e.owner_user_id or a.budget_account_id <> e.budget_account_id then
  raise exception 'approval invalid or expired'; end if;
 select * into b from public.generation_budget_accounts where id=e.budget_account_id for update;
 if not found or not b.enabled or b.owner_user_id <> e.owner_user_id or nullif(btrim(b.provider_subject),'') is null then
  raise exception 'trusted wallet allocation not enabled' using errcode='42501'; end if;
 select * into r from public.generation_requests where id=p_request and execution_id=p_execution;
 if not found or r.state <> 'PENDING' or not (r.model_id = any(a.approved_models)) then raise exception 'request or model invalid'; end if;
 select id into v_id from public.generation_budget_ledger
 where budget_account_id=b.id and idempotency_key=p_idempotency and execution_id=p_execution
   and request_id=p_request and entry_type='RESERVE' and amount_pollen=p_amount;
 if v_id is not null then return v_id; end if;
 if exists(select 1 from public.generation_budget_ledger where budget_account_id=b.id and idempotency_key=p_idempotency)
 then raise exception 'idempotency conflict'; end if;
 select coalesce(sum(amount_pollen),0) into v_total from public.generation_budget_ledger
 where execution_id=p_execution and entry_type='RESERVE';
 if v_total + p_amount > a.max_pollen then raise exception 'approval budget exceeded'; end if;
 update public.generation_budget_accounts
 set reserved_pollen=reserved_pollen+p_amount where id=b.id
 and reserved_pollen+spent_pollen+p_amount <= wallet_allocation_pollen;
 if not found then raise exception 'allocation insufficient'; end if;
 insert into public.generation_budget_ledger(budget_account_id,execution_id,request_id,entry_type,amount_pollen,idempotency_key)
 values (b.id,p_execution,p_request,'RESERVE',p_amount,p_idempotency) returning id into v_id;
 return v_id;
end $$;

create or replace function public.generation_claim_request(p_request uuid, p_owner uuid)
returns boolean language plpgsql security definer set search_path = '' as $$
declare r public.generation_requests%rowtype; e public.generation_executions%rowtype;
begin
 perform public.generation_assert_service();
 select * into r from public.generation_requests where id=p_request for update;
 if not found or r.state <> 'PENDING' then return false; end if;
 select * into e from public.generation_executions where id=r.execution_id for update;
 if e.owner_user_id <> p_owner or e.state not in ('APPROVED','RUNNING') then raise exception 'execution unauthorized'; end if;
 if exists(select 1 from public.generation_requests where execution_id=e.id
 and id <> p_request and state in ('CLAIMED','CALL_STARTED','RECONCILIATION_REQUIRED'))
 then return false; end if;
 if not exists(select 1 from public.generation_budget_ledger where request_id=p_request and entry_type='RESERVE')
 then raise exception 'request has no budget reservation'; end if;
 if exists(select 1 from public.generation_requests where execution_id=e.id and slide_index < r.slide_index
 and state <> 'SUCCEEDED') then return false; end if;
 update public.generation_requests set state='CLAIMED' where id=p_request;
 update public.generation_executions set state='RUNNING' where id=e.id;
 return true;
end $$;

create or replace function public.generation_record_result(p_request uuid, p_owner uuid, p_result text, p_evidence jsonb)
returns boolean language plpgsql security definer set search_path = '' as $$
declare r public.generation_requests%rowtype; e public.generation_executions%rowtype; v_state text;
begin
 perform public.generation_assert_service();
 if p_result not in ('SUCCEEDED','FAILED','AMBIGUOUS') or jsonb_typeof(p_evidence) <> 'object' then raise exception 'invalid result'; end if;
 select * into r from public.generation_requests where id=p_request for update;
 if not found then raise exception 'unknown request'; end if;
 select * into e from public.generation_executions where id=r.execution_id for update;
 if e.owner_user_id <> p_owner then raise exception 'owner mismatch' using errcode='42501'; end if;
 -- CALL_STARTED must be recorded by a separate controlled dispatcher before any provider call.
 if r.state <> 'CALL_STARTED' then raise exception 'provider call not recorded'; end if;
 v_state := case when p_result='AMBIGUOUS' then 'RECONCILIATION_REQUIRED' else p_result end;
 update public.generation_requests set state=v_state where id=p_request;
 if v_state='RECONCILIATION_REQUIRED' then
  update public.generation_executions set state='RECONCILIATION_REQUIRED' where id=e.id;
 end if;
 insert into public.generation_events(execution_id,request_id,event_type,evidence)
 values(e.id,p_request,'PROVIDER_RESULT_'||v_state,p_evidence);
 return true;
end $$;

create or replace function public.generation_finalize_execution(p_execution uuid, p_owner uuid)
returns boolean language plpgsql security definer set search_path = '' as $$
declare e public.generation_executions%rowtype;
begin
 perform public.generation_assert_service();
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.owner_user_id <> p_owner then raise exception 'owner mismatch' using errcode='42501'; end if;
 if e.state='COMPLETED' then return true; end if;
 if e.state <> 'RUNNING' or not exists(select 1 from public.generation_requests where execution_id=e.id)
 or exists(select 1 from public.generation_requests where execution_id=e.id and state <> 'SUCCEEDED')
 or exists(select 1 from public.generation_budget_ledger where execution_id=e.id and entry_type='RESERVE')
 then raise exception 'execution not settled or complete'; end if;
 update public.generation_executions set state='COMPLETED' where id=e.id;
 return true;
end $$;

-- Explicit EXECUTE grants; no direct client calls.
revoke all on function public.generation_assert_service() from public, anon, authenticated;
revoke all on function public.generation_create_execution(uuid,uuid,text,jsonb) from public, anon, authenticated;
revoke all on function public.generation_approve_execution(uuid,uuid) from public, anon, authenticated;
revoke all on function public.generation_reserve_budget(uuid,uuid,numeric,text) from public, anon, authenticated;
revoke all on function public.generation_claim_request(uuid,uuid) from public, anon, authenticated;
revoke all on function public.generation_record_result(uuid,uuid,text,jsonb) from public, anon, authenticated;
revoke all on function public.generation_finalize_execution(uuid,uuid) from public, anon, authenticated;
grant execute on function public.generation_assert_service() to service_role;
grant execute on function public.generation_create_execution(uuid,uuid,text,jsonb) to service_role;
grant execute on function public.generation_approve_execution(uuid,uuid) to service_role;
grant execute on function public.generation_reserve_budget(uuid,uuid,numeric,text) to service_role;
grant execute on function public.generation_claim_request(uuid,uuid) to service_role;
grant execute on function public.generation_record_result(uuid,uuid,text,jsonb) to service_role;
grant execute on function public.generation_finalize_execution(uuid,uuid) to service_role;
