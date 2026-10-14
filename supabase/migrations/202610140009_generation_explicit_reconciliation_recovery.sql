-- Explicit recovery ONLY after the original ambiguous slide is independently
-- reconciled as SUCCEEDED. Never re-dispatch or retry a CALL_STARTED request.
begin;
create or replace function generation_internal.guard_immutable() returns trigger
language plpgsql security invoker set search_path = pg_catalog as $$
begin
    if TG_OP = 'DELETE' or TG_ARGV[0] = '' then
        raise exception 'generation audit rows cannot be changed or deleted' using errcode = '23514';
    end if;
    if (to_jsonb(NEW) - string_to_array(TG_ARGV[0], ',')) is distinct from
       (to_jsonb(OLD) - string_to_array(TG_ARGV[0], ',')) then
        raise exception 'generation binding and snapshot are immutable' using errcode = '23514';
    end if;
    if TG_TABLE_NAME in ('generation_executions','generation_requests') then
        if NEW.state <> OLD.state then
            if not ((OLD.state in ('CLAIMED','PENDING') and NEW.state = 'CALL_STARTED') or
                    (OLD.state = 'CALL_STARTED' and NEW.state in ('SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_RECONCILE')) or
                    (OLD.state = 'UNKNOWN_RECONCILE' and NEW.state in ('SUCCEEDED','FAILED_CONFIRMED')) or
                    (TG_TABLE_NAME = 'generation_executions' and OLD.state = 'UNKNOWN_RECONCILE' and NEW.state = 'CALL_STARTED')) then
                raise exception 'unsafe generation state transition; reconciliation required' using errcode = '23514';
            end if;
        end if;
        if OLD.call_started_at is not null and NEW.call_started_at is distinct from OLD.call_started_at then
            raise exception 'call start is immutable once recorded' using errcode = '23514';
        end if;
    end if;
    if TG_TABLE_NAME = 'generation_requests' then
        if OLD.output_sha256 is not null and
           (NEW.output_bucket,NEW.output_object_key,NEW.output_object_version,NEW.output_sha256) is distinct from
           (OLD.output_bucket,OLD.output_object_key,OLD.output_object_version,OLD.output_sha256) then
            raise exception 'output storage reference is immutable' using errcode = '23514';
        end if;
    end if;
    return NEW;
end;
$$;


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
 if not exists(select 1 from public.generation_requests where execution_id=e.id and state='PENDING')
 then raise exception 'nothing to resume; settle instead'; end if;
 if exists(select 1 from public.generation_requests r where r.execution_id=e.id
   and r.state='PENDING' and exists(select 1 from public.generation_requests earlier
     where earlier.execution_id=e.id and earlier.slide_ordinal<r.slide_ordinal
     and earlier.state<>'SUCCEEDED'))
 then raise exception 'sequential slide fence failed'; end if;
 update public.generation_executions set state='CALL_STARTED',revision=revision+1 where id=e.id;
 return true;
end $$;
revoke all on function public.generation_resume_after_reconciliation(uuid,uuid,text,text)
 from public,anon,authenticated;
grant execute on function public.generation_resume_after_reconciliation(uuid,uuid,text,text)
 to service_role;
commit;
