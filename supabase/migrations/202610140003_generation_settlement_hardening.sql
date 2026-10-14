-- P2-B1 safety hardening: settle a reservation atomically; no provider execution.
-- A provider result is NOT sufficient to authorize a debit: trusted reconciliation
-- evidence must be verified by the service before invoking this RPC.
create or replace function public.generation_settle_reservation(
 p_request uuid, p_owner uuid, p_actual numeric, p_evidence jsonb,
 p_idempotency text
) returns uuid language plpgsql security definer set search_path = '' as $$
declare
 r public.generation_requests%rowtype;
 e public.generation_executions%rowtype;
 b public.generation_budget_accounts%rowtype;
 v_reserved numeric;
 v_settled numeric;
 v_released numeric;
 v_id uuid;
begin
 perform public.generation_assert_service();
 if p_actual is null or p_actual < 0 or p_idempotency is null
 or nullif(btrim(p_idempotency),'') is null
 or jsonb_typeof(p_evidence) <> 'object' then
  raise exception 'invalid settlement inputs';
 end if;
 select * into r from public.generation_requests where id=p_request for update;
 if not found then raise exception 'request missing'; end if;
 select * into e from public.generation_executions where id=r.execution_id for update;
 if e.owner_user_id <> p_owner then raise exception 'owner mismatch' using errcode='42501'; end if;
 -- No automatic settlement of ambiguous/failed provider outcomes.
 if r.state <> 'SUCCEEDED' then raise exception 'request not reconciled as succeeded'; end if;
 select * into b from public.generation_budget_accounts where id=e.budget_account_id for update;
 if b.owner_user_id <> p_owner then raise exception 'wallet mismatch' using errcode='42501'; end if;
 select coalesce(sum(amount_pollen),0) into v_reserved
 from public.generation_budget_ledger where request_id=p_request and entry_type='RESERVE';
 if v_reserved <= 0 or p_actual > v_reserved then
  raise exception 'actual cost exceeds reservation or reservation missing';
 end if;
 select id into v_id from public.generation_budget_ledger
 where budget_account_id=b.id and idempotency_key=p_idempotency
 and request_id=p_request and entry_type='SETTLE' and amount_pollen=p_actual;
 if v_id is not null then return v_id; end if;
 if exists(select 1 from public.generation_budget_ledger where budget_account_id=b.id and idempotency_key=p_idempotency)
 then raise exception 'idempotency conflict'; end if;
 if exists(select 1 from public.generation_budget_ledger where request_id=p_request and entry_type in ('SETTLE','RELEASE'))
 then raise exception 'request already settled or released'; end if;
 -- Zero actual cost: a RELEASE row alone represents final settlement.
 v_released := v_reserved-p_actual;
 update public.generation_budget_accounts
 set reserved_pollen=reserved_pollen-v_reserved,
 spent_pollen=spent_pollen+p_actual
 where id=b.id and reserved_pollen >= v_reserved;
 if not found then raise exception 'wallet reservation drift'; end if;
 if p_actual > 0 then
  insert into public.generation_budget_ledger
   (budget_account_id,execution_id,request_id,entry_type,amount_pollen,idempotency_key)
  values (b.id,e.id,p_request,'SETTLE',p_actual,p_idempotency) returning id into v_id;
 end if;
 if v_released > 0 then
  insert into public.generation_budget_ledger
   (budget_account_id,execution_id,request_id,entry_type,amount_pollen,idempotency_key)
  values (b.id,e.id,p_request,'RELEASE',v_released,p_idempotency||':release')
  returning id into v_id;
 end if;
 insert into public.generation_events(execution_id,request_id,event_type,evidence)
 values (e.id,p_request,'BUDGET_SETTLED',p_evidence);
 return v_id;
end $$;

-- PostgreSQL grants EXECUTE to PUBLIC by default for newly created functions.
-- Revoke PUBLIC (not just named roles), then explicitly grant service_role.
revoke all on function public.generation_assert_service() from public;
revoke all on function public.generation_create_execution(uuid,uuid,text,jsonb) from public;
revoke all on function public.generation_approve_execution(uuid,uuid) from public;
revoke all on function public.generation_reserve_budget(uuid,uuid,numeric,text) from public;
revoke all on function public.generation_claim_request(uuid,uuid) from public;
revoke all on function public.generation_record_result(uuid,uuid,text,jsonb) from public;
revoke all on function public.generation_finalize_execution(uuid,uuid) from public;
revoke all on function public.generation_settle_reservation(uuid,uuid,numeric,jsonb,text) from public, anon, authenticated;
grant execute on function public.generation_settle_reservation(uuid,uuid,numeric,jsonb,text) to service_role;
