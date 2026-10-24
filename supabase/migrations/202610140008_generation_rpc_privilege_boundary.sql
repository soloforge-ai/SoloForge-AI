-- RPC-only DML boundary for generation tables.
-- Applied after functions are created. Function owners must be the migration
-- owner, not service_role. PostgreSQL superuser is used ONLY in disposable CI.
begin;
alter function public.generation_reserve_execution(uuid,uuid,text,text) security definer;
alter function public.generation_settle_execution(uuid,uuid,text,numeric,text) security definer;
alter function public.generation_mark_call_started(uuid,uuid,text) security definer;
alter function public.generation_record_verified_result(uuid,uuid,text,text,text,numeric,text,text,text,text) security definer;
-- Remove direct INSERT for every generation table.
revoke insert on public.generation_budget_accounts,public.generation_approvals,
 public.generation_executions,public.generation_requests,
 public.generation_budget_ledger,public.generation_events from service_role;
-- Revoke column-level UPDATE grants from original Phase 1.
revoke update (allocation_state,allocation_ref,allocation_verified_at,allocated_pollen,reserved_pollen,spent_pollen,revision)
 on public.generation_budget_accounts from service_role;
revoke update (state,revoked_at,revision) on public.generation_approvals from service_role;
revoke update (state,observed_pollen,call_started_at,settled_at,revision)
 on public.generation_executions from service_role;
revoke update (state,call_started_at,completed_at,provider_request_ref,observed_pollen,
 output_bucket,output_object_key,output_object_version,output_sha256)
 on public.generation_requests from service_role;
-- Prevent default PUBLIC execute for every RPC.
revoke all on function public.generation_reserve_execution(uuid,uuid,text,text) from public,anon,authenticated;
revoke all on function public.generation_settle_execution(uuid,uuid,text,numeric,text) from public,anon,authenticated;
revoke all on function public.generation_mark_call_started(uuid,uuid,text) from public,anon,authenticated;
revoke all on function public.generation_record_verified_result(uuid,uuid,text,text,text,numeric,text,text,text,text) from public,anon,authenticated;
commit;
