-- Local OFFLINE APPLICATION candidate only; after existing Cloudflare/BYOP SQL.
-- No activation, secret keys, verification or budget provisioning.
begin;
create function public.byop_cloudflare_credentials(p_principal text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
 perform public.byop_assert_principal(p_principal);
 select coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) into result from (
  select id as credential_id,provider_account_id as account_id,verification_status,expires_at,
    byop_revoked_at is not null as disconnected,provider_ownership_verified
  from public.pollinations_sessions where credential_provider='cloudflare' and
   ((split_part(p_principal,':',1)='owner' and submitted_by_owner=split_part(p_principal,':',2)::uuid)
    or (split_part(p_principal,':',1)='member' and submitted_by_member=split_part(p_principal,':',2)::uuid))
  order by updated_at desc limit 50) r;
 return result;
end;
$$;
create function public.byop_cloudflare_job(p_principal text,p_prompt text,p_model text,p_mode text default 'offline_mock') returns jsonb
language plpgsql security invoker set search_path='' as $$
declare job public.content_jobs;
begin
 perform public.byop_assert_principal(p_principal);
 if p_mode is null or p_mode not in ('offline_mock','cloudflare_http')
  or split_part(p_principal,':',1)<>'owner' or p_model is distinct from '@cf/black-forest-labs/flux-1-schnell'
  or p_prompt is null or length(btrim(p_prompt)) not between 1 and 2048 then raise exception 'Invalid Owner mock image job'; end if;
 insert into public.content_jobs(idea,source,status,qa_status,byop_principal,byop_model,script,content_package)
 values('Cloudflare offline image','app_byop','ASSET_QUEUED','PENDING',p_principal,p_model,'',
  jsonb_build_object('byop_principal',p_principal,'byop_provider','cloudflare','offline_mock',p_mode='offline_mock','generation_mode',p_mode,
   'asset_forge_request',jsonb_build_object('prompt',p_prompt,'model',p_model),
   'ceo_identity_required',false,'pipeline_route','TEXT')) returning * into job;
 return to_jsonb(job);
end;
$$;
revoke all on function public.byop_cloudflare_credentials(text),public.byop_cloudflare_job(text,text,text,text) from public,anon,authenticated;
grant execute on function public.byop_cloudflare_credentials(text),public.byop_cloudflare_job(text,text,text,text) to service_role;

create or replace function public.byop_job_binding_immutable() returns trigger
language plpgsql set search_path='' as $$
begin
    if new.byop_principal is distinct from old.byop_principal then
        raise exception 'Job principal is immutable';
    end if;
    if old.byop_principal is not null and (
        new.byop_revision is distinct from old.byop_revision or new.byop_model is distinct from old.byop_model
        or new.script is distinct from old.script
        or new.content_package->'asset_forge_request' is distinct from old.content_package->'asset_forge_request'
        or new.content_package->>'byop_principal' is distinct from old.byop_principal
        or new.content_package->>'pipeline_route' is distinct from old.content_package->>'pipeline_route'
        or new.content_package->'byop_provider' is distinct from old.content_package->'byop_provider'
        or new.content_package->'offline_mock' is distinct from old.content_package->'offline_mock'
        or new.content_package->'generation_mode' is distinct from old.content_package->'generation_mode'
        or new.content_package->'ceo_identity_required' is distinct from
            case when old.content_package->>'byop_provider'='cloudflare' then 'false'::jsonb else 'true'::jsonb end) then
        raise exception 'BYOP job request/revision is immutable; create a new job';
    end if;
    return new;
end;
$$;

create or replace function public.byop_cloudflare_claim(p_principal text,p_execution uuid,p_snapshot jsonb,p_snapshot_hash text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare cred public.pollinations_sessions; current_state jsonb; rev bigint; execution jsonb; consent jsonb; job public.content_jobs;
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
 if p_snapshot->'settings'->'job_bound'='true'::jsonb then
  select * into job from public.content_jobs where id=(p_snapshot->>'job_id')::uuid
   and byop_principal=p_principal for update;
  if job.id is null or job.status is distinct from 'ASSET_QUEUED'
   or job.byop_revision::text is distinct from p_snapshot->>'revision'
   or job.byop_model is distinct from p_snapshot->>'model'
   or job.content_package->>'byop_provider' is distinct from 'cloudflare'
   or coalesce(job.content_package->>'generation_mode','offline_mock') is distinct from
       coalesce(p_snapshot->'settings'->>'transport_mode','offline_mock')
   or encode(sha256(convert_to(job.content_package->'asset_forge_request'->>'prompt','UTF8')),'hex') is distinct from p_snapshot->>'prompt_sha256'
   then raise exception 'Mock image job changed or already claimed'; end if;
  update public.content_jobs set status='ASSET_GENERATING' where id=job.id;
 end if;
 execution:=execution||jsonb_build_object('state','CALL_STARTED','started_at',extract(epoch from clock_timestamp()));
 current_state:=jsonb_set(current_state,array['executions',p_execution::text],execution);
 if not public.byop_ledger_cas(p_principal,rev,current_state) then raise exception 'Claim failed'; end if;
 return execution;
end;
$$;

create or replace function public.byop_job_update(p_principal text,p_id uuid,p_revision bigint,p_action text,p_value jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare job public.content_jobs; package jsonb; sha text; decision text; next_status text;
begin
    perform public.byop_assert_principal(p_principal);
    select * into job from public.content_jobs where id=p_id and byop_principal=p_principal and byop_revision=p_revision for update;
    if not found then raise exception 'Job unavailable or changed'; end if;
    package:=job.content_package;
    if package->>'byop_provider'='cloudflare' and p_action not in ('asset','review') then
        raise exception 'Cloudflare mock jobs have no media or publishing route'; end if;
    if p_action='asset' and package->>'byop_provider'='cloudflare' then
        sha:=p_value->>'sha256';
        if job.status is distinct from 'ASSET_GENERATING' or sha is null or sha !~ '^[0-9a-f]{64}$'
          or p_value->>'path' is distinct from p_id::text||'/'||sha||'.png'
          or coalesce(package->>'generation_mode','offline_mock') not in ('offline_mock','cloudflare_http')
          or package->'ceo_identity_required' is distinct from 'false'::jsonb
          or p_value->'manifest'->>'provider' is distinct from 'cloudflare'
          or p_value->'manifest'->>'generation_mode' is distinct from coalesce(package->>'generation_mode','offline_mock')
          or p_value->'manifest'->>'generation_layout' is distinct from 'text_image'
          or p_value->'manifest'->>'model' is distinct from job.byop_model
          or p_value->'branding'->'brand_applied' is distinct from 'true'::jsonb then
            raise exception 'Invalid offline image outcome'; end if;
        package:=package||jsonb_build_object('asset_sha256',sha,'asset_storage_path',p_value->>'path',
          'asset_status','READY','asset_review_status','PENDING','asset_review_sha256',null,
          'asset_provider','cloudflare','asset_mode',coalesce(package->>'generation_mode','offline_mock'),'asset_forge_manifest',p_value->'manifest')||(p_value->'branding');
        update public.content_jobs set content_package=package,status='READY_FOR_REVIEW',qa_status='PENDING' where id=p_id;
    elsif p_action='asset' then
        sha:=p_value->>'sha256';
        if job.status is distinct from 'ASSET_GENERATING' or sha is null or sha !~ '^[0-9a-f]{64}$'
            or p_value->>'path'<>p_id::text||'/'||sha||'.png'
            or p_value->'manifest'->>'generation_layout' is distinct from 'single_character'
            or p_value->'manifest'->>'generation_mode' is distinct from 'pollinations'
            or lower(p_value->'manifest'->>'character') is distinct from 'ceo'
            or p_value->'branding'->'brand_applied' is distinct from 'true'::jsonb then
            raise exception 'Invalid asset outcome'; end if;
        package:=package||jsonb_build_object('asset_sha256',sha,'asset_storage_path',p_value->>'path',
            'asset_status','READY','asset_review_status','PENDING','asset_review_sha256',null,
            'asset_provider','pollinations','asset_mode','ai_generated',
            'asset_forge_manifest',p_value->'manifest')||(p_value->'branding');
        update public.content_jobs set content_package=package,status='READY_FOR_REVIEW',qa_status='PENDING' where id=p_id;
    elsif p_action='review' then
        sha:=p_value->>'sha256'; decision:=p_value->>'decision';
        if job.status<>'READY_FOR_REVIEW' or package->>'asset_status'<>'READY'
            or sha is distinct from package->>'asset_sha256' or decision not in ('APPROVED','REJECTED')
            or (decision='APPROVED' and upper(package->'semantic_fidelity'->>'status') in ('FAIL','STALE')) then
            raise exception 'Current image/semantic approval required'; end if;
        package:=package||jsonb_build_object('asset_review_status',decision,
            'asset_review_sha256',case when decision='APPROVED' then sha else null end,
            'asset_reviewed_at',clock_timestamp());
        update public.content_jobs set content_package=package,
            status=case when decision='APPROVED' then 'ASSET_READY' else 'READY_FOR_REVIEW' end,
            qa_status=case when decision='APPROVED' then 'PASS' else 'FAIL' end where id=p_id;
    elsif p_action='audio' then
        if job.status<>'ASSET_READY' or package->>'asset_review_status'<>'APPROVED'
            or package->>'asset_review_sha256' is distinct from package->>'asset_sha256'
            or p_value->>'path' !~ ('^'||p_id::text||'/[0-9a-f]{64}[.]wav$') then raise exception 'Approved job audio required'; end if;
        update public.content_jobs set audio_storage_path=p_value->>'path',status='AUDIO_READY' where id=p_id;
    elsif p_action='render' then
        if job.status<>'AUDIO_READY' or package->>'asset_review_status'<>'APPROVED'
            or package->>'asset_review_sha256' is distinct from package->>'asset_sha256'
            or job.video_url is not null then raise exception 'Approved image/audio required'; end if;
        update public.content_jobs set status='FINAL_RENDERING',render_status='PROCESSING' where id=p_id;
    else raise exception 'Unknown job action'; end if;
    select * into job from public.content_jobs where id=p_id;
    return to_jsonb(job);
end;
$$;
-- All helper/RPC entry points are backend-only; clients cannot supply a principal
-- directly to SQL. HTTP derives it from Owner V2 or Supabase + active membership.

commit;
