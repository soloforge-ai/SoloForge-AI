-- Reconcile finalization against settled request reservations, not historical RESERVE rows.
create or replace function public.generation_finalize_execution(p_execution uuid, p_owner uuid)
returns boolean language plpgsql security definer set search_path = '' as $$
declare e public.generation_executions%rowtype;
begin
 perform public.generation_assert_service();
 select * into e from public.generation_executions where id=p_execution for update;
 if not found or e.owner_user_id <> p_owner then
  raise exception 'owner mismatch' using errcode='42501';
 end if;
 if e.state='COMPLETED' then return true; end if;
 if e.state <> 'RUNNING' then raise exception 'execution not running'; end if;
 if not exists(select 1 from public.generation_requests where execution_id=e.id)
 or exists(
  select 1 from public.generation_requests r
  where r.execution_id=e.id and (
   r.state <> 'SUCCEEDED'
   or not exists(select 1 from public.generation_budget_ledger l
                 where l.request_id=r.id and l.entry_type in ('SETTLE','RELEASE'))
  )
 ) then raise exception 'requests not fully reconciled and settled'; end if;
 update public.generation_executions set state='COMPLETED' where id=e.id;
 return true;
end $$;
revoke all on function public.generation_finalize_execution(uuid,uuid) from public, anon, authenticated;
grant execute on function public.generation_finalize_execution(uuid,uuid) to service_role;
