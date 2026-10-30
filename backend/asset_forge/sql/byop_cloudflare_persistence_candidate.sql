-- Local offline candidate ONLY, after retained owner-binding/BYOP candidates.
-- No new credential table, key material, activation, budgets or provider calls.
begin;
alter table public.pollinations_sessions
 add column credential_provider text not null default 'pollinations' check (credential_provider in ('pollinations','cloudflare')),
 add column provider_account_id text,
 add column secret_ciphertext text,
 add column secret_key_id text,
 add column secret_sha256 text,
 add column independent_verification_evidence text,
 add constraint byop_encrypted_cloudflare check (
  (credential_provider='pollinations' and secret_ciphertext is null and secret_key_id is null and secret_sha256 is null and provider_account_id is null)
  or (credential_provider='cloudflare' and access_token='encrypted:v1:'||id::text
      and provider_account_id ~ '^[0-9a-f]{32}$' and provider_account_id is not null
      and length(secret_ciphertext)>32 and secret_ciphertext is not null
      and length(secret_key_id)>0 and secret_key_id is not null
      and secret_sha256 ~ '^[0-9a-f]{64}$' and secret_sha256 is not null
      and (verification_status='PENDING_VERIFICATION' or
          (provider_subject=provider_account_id and byop_verified_at is not null
           and length(btrim(independent_verification_evidence))>0 and independent_verification_evidence is not null))));
create unique index byop_cloudflare_secret_identity on public.pollinations_sessions(secret_sha256)
 where credential_provider='cloudflare';
create function public.byop_provider_identity_guard() returns trigger
language plpgsql set search_path='' as $$
begin
 if new.credential_provider is distinct from old.credential_provider
   or new.provider_account_id is distinct from old.provider_account_id
   or new.secret_ciphertext is distinct from old.secret_ciphertext
   or new.secret_key_id is distinct from old.secret_key_id
   or new.secret_sha256 is distinct from old.secret_sha256 then
   raise exception 'Provider credential identity is immutable';
 end if;
 if old.credential_provider='cloudflare' and current_user<>'postgres' and (
   new.verification_status is distinct from old.verification_status
   or new.provider_ownership_verified is distinct from old.provider_ownership_verified
   or new.provider_subject is distinct from old.provider_subject
   or new.independent_verification_evidence is distinct from old.independent_verification_evidence
   or new.byop_verified_at is distinct from old.byop_verified_at
   or new.expires_at is distinct from old.expires_at) then
   raise exception 'Independent administrative verification required';
 end if;
 return new;
end;
$$;
create trigger byop_provider_identity_guard before update on public.pollinations_sessions
 for each row execute function public.byop_provider_identity_guard();
revoke all on function public.byop_provider_identity_guard() from public,anon,authenticated;

create function public.byop_cloudflare_submit(p_principal text,p_id uuid,p_account text,
 p_ciphertext text,p_key_id text,p_token_sha256 text) returns jsonb
language plpgsql security invoker set search_path='' as $$
begin
 perform public.byop_assert_principal(p_principal);
 insert into public.pollinations_sessions(id,session_id,access_token,expires_at,
  submitted_by_owner,submitted_by_member,credential_provider,provider_account_id,
  secret_ciphertext,secret_key_id,secret_sha256)
 values(p_id,'cf:'||p_id::text,'encrypted:v1:'||p_id::text,clock_timestamp()+interval '10 minutes',
  case when split_part(p_principal,':',1)='owner' then split_part(p_principal,':',2)::uuid end,
  case when split_part(p_principal,':',1)='member' then split_part(p_principal,':',2)::uuid end,
  'cloudflare',p_account,p_ciphertext,p_key_id,p_token_sha256);
 return jsonb_build_object('credential_id',p_id,'verification_status','PENDING_VERIFICATION','spending_authorized',false);
end;
$$;
create function public.byop_cloudflare_credential(p_principal text,p_id uuid) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
 perform public.byop_assert_principal(p_principal);
 select to_jsonb(s) into result from public.pollinations_sessions s where id=p_id and credential_provider='cloudflare'
  and ((split_part(p_principal,':',1)='owner' and submitted_by_owner=split_part(p_principal,':',2)::uuid)
    or (split_part(p_principal,':',1)='member' and submitted_by_member=split_part(p_principal,':',2)::uuid)) for share;
 return result;
end;
$$;
create function public.byop_cloudflare_disconnect(p_principal text,p_id uuid) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 if public.byop_cloudflare_credential(p_principal,p_id) is null then return false; end if;
 update public.pollinations_sessions set byop_revoked_at=coalesce(byop_revoked_at,clock_timestamp()) where id=p_id;
 return found;
end;
$$;
create function public.byop_cloudflare_claim(p_principal text,p_execution uuid,p_snapshot jsonb,p_snapshot_hash text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare cred public.pollinations_sessions; current_state jsonb; rev bigint; execution jsonb; consent jsonb;
begin
 -- Identity/membership is locked by the reused principal assertion. Revocation
 -- and claim serialize on the same credential row, then the existing ledger.
 perform public.byop_assert_principal(p_principal);
 if split_part(p_principal,':',1)<>'owner' then raise exception 'Member generation disabled'; end if;
 select * into cred from public.pollinations_sessions where id=(p_snapshot->>'credential_id')::uuid
   and submitted_by_owner=split_part(p_principal,':',2)::uuid and credential_provider='cloudflare' for update;
 if cred.id is null or cred.byop_revoked_at is not null or cred.expires_at<=clock_timestamp()
   or cred.verification_status<>'VERIFIED' or not cred.provider_ownership_verified
   or cred.secret_sha256 is distinct from p_snapshot->>'credential_sha256'
   or cred.provider_account_id is distinct from p_snapshot->>'account_id'
   or p_snapshot->>'provider' is distinct from 'cloudflare' or p_snapshot->>'budget_unit' is distinct from 'neurons'
   or p_snapshot->>'operation' is distinct from 'text_image' then raise exception 'Credential dispatch denied'; end if;
 select revision,state into rev,current_state from public.byop_ledgers where principal=p_principal for update;
 if current_state->>'provider' is distinct from 'cloudflare' or current_state->>'unit' is distinct from 'neurons' then
  raise exception 'Provider budget mismatch'; end if;
 execution:=current_state->'executions'->p_execution::text;
 consent:=current_state->'consents'->(execution->>'consent_id');
 if execution is null or execution->>'state' is distinct from 'RESERVED'
  or execution->>'principal' is distinct from p_principal
  or execution->'snapshot' is distinct from p_snapshot
  or execution->>'snapshot_sha256' is distinct from p_snapshot_hash
  or (execution->>'expires_at')::numeric<=extract(epoch from clock_timestamp())
  or consent is null or consent->'used' is distinct from 'true'::jsonb
  or consent->'snapshot' is distinct from p_snapshot
  or consent->'quote'->>'provider' is distinct from 'cloudflare'
  or consent->'quote'->>'unit' is distinct from 'neurons'
  or consent->'quote'->'includes_all_charges' is distinct from 'true'::jsonb
  or execution->'reserved' is distinct from consent->'quote'->'maximum_neurons' then
  raise exception 'Execution cannot be claimed'; end if;
 execution:=execution||jsonb_build_object('state','CALL_STARTED','started_at',extract(epoch from clock_timestamp()));
 current_state:=jsonb_set(current_state,array['executions',p_execution::text],execution);
 if not public.byop_ledger_cas(p_principal,rev,current_state) then raise exception 'Claim failed'; end if;
 return execution;
end;
$$;
revoke all on function public.byop_cloudflare_submit(text,uuid,text,text,text,text),
 public.byop_cloudflare_credential(text,uuid),public.byop_cloudflare_disconnect(text,uuid),
 public.byop_cloudflare_claim(text,uuid,jsonb,text) from public,anon,authenticated;
grant execute on function public.byop_cloudflare_submit(text,uuid,text,text,text,text),
 public.byop_cloudflare_credential(text,uuid),public.byop_cloudflare_disconnect(text,uuid),
 public.byop_cloudflare_claim(text,uuid,jsonb,text) to service_role;

-- Keep existing Pollinations RPCs provider-scoped.
create or replace function public.byop_credential(p_principal text,p_id uuid) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
    perform public.byop_assert_principal(p_principal);
    select to_jsonb(s) into result from public.pollinations_sessions s where id=p_id and credential_provider='pollinations'
        and ((split_part(p_principal,':',1)='owner' and submitted_by_owner=split_part(p_principal,':',2)::uuid)
          or (split_part(p_principal,':',1)='member' and submitted_by_member=split_part(p_principal,':',2)::uuid)) for share;
    return result;
end;
$$;

-- Keep existing Pollinations RPCs provider-scoped.
create or replace function public.byop_credentials(p_principal text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
    perform public.byop_assert_principal(p_principal);
    select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
        select id as credential_id,verification_status,expires_at,
            (byop_revoked_at is not null) as disconnected,provider_ownership_verified
        from public.pollinations_sessions where credential_provider='pollinations' and (
            (split_part(p_principal,':',1)='owner' and submitted_by_owner=split_part(p_principal,':',2)::uuid)
            or (split_part(p_principal,':',1)='member' and submitted_by_member=split_part(p_principal,':',2)::uuid)
        ) order by updated_at desc limit 50
    ) rows;
    return result;
end;
$$;

create or replace function public.byop_ledger_cas(p_principal text, p_revision bigint, p_state jsonb)
returns boolean language plpgsql security invoker set search_path='' as $$
declare old_state jsonb; entry record; reserved_total bigint; active_count bigint;
begin
    select state into old_state from public.byop_ledgers
        where principal=p_principal and revision=p_revision for update;
    if not found then return false; end if;
    -- Budget and concurrency policy cannot be changed by runtime CAS.
    if old_state->'provider' is distinct from p_state->'provider' or old_state->'unit' is distinct from p_state->'unit' then
        raise exception 'Provider budget unit is immutable';
    end if;
    if old_state->'budget' is distinct from p_state->'budget'
        or old_state->'concurrency_limit' is distinct from p_state->'concurrency_limit'
        or old_state->'settled' is distinct from p_state->'settled' then
        raise exception 'Administrative budget policy is immutable';
    end if;
    select coalesce(sum((value->>'reserved')::bigint),0), count(*) into reserved_total,active_count
        from jsonb_each(coalesce(p_state->'executions','{}'))
        where value->>'state' in ('RESERVED','CALL_STARTED','UNKNOWN','GENERATED');
    if reserved_total + coalesce((p_state->>'settled')::bigint,0) > (p_state->>'budget')::bigint
        or active_count > (p_state->>'concurrency_limit')::bigint then
        raise exception 'Principal budget or concurrency exceeded';
    end if;
    for entry in select key,value from jsonb_each(coalesce(old_state->'consents','{}')) loop
        if (entry.value - 'used') is distinct from ((p_state->'consents'->entry.key) - 'used')
            or (entry.value->'used' = 'true'::jsonb
                and p_state->'consents'->entry.key->'used' is distinct from 'true'::jsonb) then
            raise exception 'Consent terms and quoted evidence are immutable';
        end if;
    end loop;
    for entry in select key,value from jsonb_each(coalesce(p_state->'executions','{}')) loop
        if entry.value->>'principal' is distinct from p_principal
            or (entry.value->>'reserved')::bigint <= 0
            or entry.value->>'state' not in ('RESERVED','CALL_STARTED','UNKNOWN','GENERATED') then
            raise exception 'Invalid principal execution';
        end if;
    end loop;
    for entry in select key,value from jsonb_each(coalesce(old_state->'executions','{}')) loop
        if not (p_state->'executions' ? entry.key)
            or entry.value->'snapshot' is distinct from p_state->'executions'->entry.key->'snapshot'
            or entry.value->'snapshot_sha256' is distinct from p_state->'executions'->entry.key->'snapshot_sha256'
            or entry.value->'quote_sha256' is distinct from p_state->'executions'->entry.key->'quote_sha256'
            or (entry.value ? 'dispatch_evidence' and entry.value->'dispatch_evidence'
                is distinct from p_state->'executions'->entry.key->'dispatch_evidence')
            or entry.value->'reserved' is distinct from p_state->'executions'->entry.key->'reserved'
            or entry.value->'principal' is distinct from p_state->'executions'->entry.key->'principal'
            or entry.value->'consent_id' is distinct from p_state->'executions'->entry.key->'consent_id' then
            raise exception 'Execution snapshot is immutable';
        end if;
        if (entry.value->>'state' in ('UNKNOWN','GENERATED')
            and entry.value->>'state' is distinct from p_state->'executions'->entry.key->>'state')
            or (entry.value->>'state' = 'CALL_STARTED'
                and p_state->'executions'->entry.key->>'state' = 'RESERVED') then
            raise exception 'Execution replay forbidden';
        end if;
    end loop;
    update public.byop_ledgers set state=p_state, revision=revision+1, updated_at=now()
        where principal=p_principal and revision=p_revision;
    return found;
end;
$$;

commit;
