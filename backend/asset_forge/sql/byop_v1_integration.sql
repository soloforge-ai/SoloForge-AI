-- Local additive candidate. Apply only after the verified #210 and BYOP candidates.
-- No seed, activation, budget provisioning or runtime enabling is performed here.
begin;
alter table public.soloforge_memberships
    add column pollinations_subject text,
    add column pollinations_verified_at timestamptz,
    add column pollinations_evidence text;
alter table public.pollinations_sessions
    add column submitted_by_member uuid references public.soloforge_memberships(user_id),
    add column byop_revoked_at timestamptz,
    add column byop_verified_at timestamptz,
    add constraint pollinations_one_principal check (not (submitted_by_owner is not null and submitted_by_member is not null));
alter table public.pollinations_sessions drop constraint pollinations_binding_consistency;
alter table public.pollinations_sessions add constraint pollinations_binding_consistency check (
    (verification_status='PENDING_VERIFICATION' and not provider_ownership_verified)
    or (verification_status='VERIFIED' and provider_ownership_verified
        and (submitted_by_owner is not null or submitted_by_member is not null)
        and provider_subject is not null and length(btrim(provider_subject)) > 0));
alter table public.pollinations_sessions drop constraint pollinations_sessions_owner_subject_together;
alter table public.pollinations_sessions add constraint pollinations_sessions_owner_subject_together check (
    (owner_user_id is null and provider_subject is null)
    or (owner_user_id is not null and provider_subject is not null and length(btrim(provider_subject)) > 0)
    or ((submitted_by_owner is not null or submitted_by_member is not null)
        and verification_status='VERIFIED' and provider_ownership_verified
        and provider_subject is not null and length(btrim(provider_subject)) > 0));
-- Extend the existing #210 guard, preserving its legacy and Owner V2 cases.
create or replace function public.pollinations_pending_insert_guard() returns trigger
language plpgsql set search_path='' as $$
begin
    if (new.submitted_by_owner is not null or new.submitted_by_member is not null)
        and new.verification_status='PENDING_VERIFICATION' and not new.provider_ownership_verified
        and not new.spending_authorized and new.owner_user_id is null and new.provider_subject is null then
        return new;
    end if;
    if new.submitted_by_owner is null and new.submitted_by_member is null
        and new.owner_user_id is not null and new.provider_subject is not null
        and length(btrim(new.provider_subject)) > 0 and new.verification_status='PENDING_VERIFICATION'
        and not new.provider_ownership_verified and not new.spending_authorized then return new; end if;
    raise check_violation using message='Authenticated principal submission required';
end;
$$;
create function public.byop_member_credential_immutable() returns trigger
language plpgsql set search_path='' as $$
begin
    if new.submitted_by_member is distinct from old.submitted_by_member
        or (old.byop_revoked_at is not null and new.byop_revoked_at is distinct from old.byop_revoked_at) then
        raise exception 'Member binding and revocation are immutable';
    end if;
    return new;
end;
$$;
create trigger byop_member_credential_immutable before update on public.pollinations_sessions
    for each row execute function public.byop_member_credential_immutable();
alter table public.content_jobs
    add column byop_principal text,
    add column byop_revision bigint not null default 1,
    add column byop_model text not null default 'kontext';
create index byop_jobs_principal on public.content_jobs(byop_principal);
alter table public.content_jobs enable row level security;
-- Restrictive policy composes with existing tenant policies; direct clients may
-- not read/write BYOP rows. BYOP uses authenticated backend operations only.
create policy byop_jobs_no_direct_client on public.content_jobs as restrictive
    for all to anon,authenticated using (byop_principal is null) with check (byop_principal is null);
create function public.byop_job_binding_immutable() returns trigger
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
        or new.content_package->'ceo_identity_required' is distinct from 'true'::jsonb) then
        raise exception 'BYOP job request/revision is immutable; create a new job';
    end if;
    return new;
end;
$$;
create trigger byop_job_binding_immutable before update on public.content_jobs
    for each row execute function public.byop_job_binding_immutable();

create function public.byop_assert_principal(p_principal text) returns void
language plpgsql security invoker set search_path='' as $$
declare uid uuid;
begin
    if p_principal !~ '^(owner|member):[0-9a-f-]{36}$' then raise exception 'Invalid principal'; end if;
    uid := split_part(p_principal,':',2)::uuid;
    if split_part(p_principal,':',1)='owner' then
        perform 1 from public.soloforge_owners where owner_id=uid and status='active' for share;
    else
        perform 1 from public.soloforge_memberships where user_id=uid and status='ACTIVE' for share;
    end if;
    if not found then raise exception 'Active principal required'; end if;
end;
$$;
create function public.byop_expected_subject(p_principal text) returns text
language plpgsql security invoker set search_path='' as $$
declare subject text;
begin
    perform public.byop_assert_principal(p_principal);
    if split_part(p_principal,':',1)='owner' then
        select provider_account_id into subject from public.soloforge_owner_accounts
            where owner_id=split_part(p_principal,':',2)::uuid and provider='pollinations'
            and verification_status='verified' and verified_at is not null
            and length(btrim(verification_evidence))>0;
    else
        select pollinations_subject into subject from public.soloforge_memberships
            where user_id=split_part(p_principal,':',2)::uuid and status='ACTIVE'
            and pollinations_verified_at is not null and length(btrim(pollinations_evidence))>0 for share;
    end if;
    return subject;
end;
$$;
create function public.byop_credential(p_principal text,p_id uuid) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
    perform public.byop_assert_principal(p_principal);
    select to_jsonb(s) into result from public.pollinations_sessions s where id=p_id
        and ((split_part(p_principal,':',1)='owner' and submitted_by_owner=split_part(p_principal,':',2)::uuid)
          or (split_part(p_principal,':',1)='member' and submitted_by_member=split_part(p_principal,':',2)::uuid)) for share;
    return result;
end;
$$;
create function public.byop_submit(p_principal text,p_token text,p_session text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare rid uuid;
begin
    perform public.byop_assert_principal(p_principal);
    if left(p_token,3)<>'sk_' or length(p_token) not between 4 and 4096 then raise exception 'Invalid credential'; end if;
    insert into public.pollinations_sessions(session_id,access_token,token_type,scope,expires_at,
        submitted_by_owner,submitted_by_member,verification_status,provider_ownership_verified,spending_authorized)
    values(p_session,p_token,'Bearer','',clock_timestamp()+interval '10 minutes',
        case when split_part(p_principal,':',1)='owner' then split_part(p_principal,':',2)::uuid end,
        case when split_part(p_principal,':',1)='member' then split_part(p_principal,':',2)::uuid end,
        'PENDING_VERIFICATION',false,false) returning id into rid;
    return jsonb_build_object('credential_id',rid,'verification_status','PENDING_VERIFICATION','spending_authorized',false);
end;
$$;
create function public.byop_credentials(p_principal text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
    perform public.byop_assert_principal(p_principal);
    select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
        select id as credential_id,verification_status,expires_at,
            (byop_revoked_at is not null) as disconnected,provider_ownership_verified
        from public.pollinations_sessions where
            (split_part(p_principal,':',1)='owner' and submitted_by_owner=split_part(p_principal,':',2)::uuid)
            or (split_part(p_principal,':',1)='member' and submitted_by_member=split_part(p_principal,':',2)::uuid)
        order by updated_at desc limit 50
    ) rows;
    return result;
end;
$$;
create function public.byop_verify(p_principal text,p_id uuid,p_subject text,p_verified boolean) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare record jsonb; expected text; verified boolean;
begin
    record:=public.byop_credential(p_principal,p_id);
    if record is null or record->>'byop_revoked_at' is not null then raise exception 'Credential unavailable'; end if;
    expected:=public.byop_expected_subject(p_principal);
    verified:=coalesce(p_verified and expected is not null and p_subject=expected
        and (record->>'expires_at')::timestamptz>clock_timestamp(),false);
    update public.pollinations_sessions set verification_status=case when verified then 'VERIFIED' else 'PENDING_VERIFICATION' end,
        provider_ownership_verified=verified,provider_subject=case when verified then p_subject
            when record->>'owner_user_id' is not null then record->>'provider_subject' else null end,
        byop_verified_at=case when verified then clock_timestamp() end where id=p_id;
    return jsonb_build_object('verification_status',case when verified then 'VERIFIED' else 'PENDING_VERIFICATION' end,
        'provider_ownership_verified',verified,'spending_authorized',false);
end;
$$;
create function public.byop_disconnect(p_principal text,p_id uuid) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
    if public.byop_credential(p_principal,p_id) is null then return false; end if;
    update public.pollinations_sessions set byop_revoked_at=coalesce(byop_revoked_at,clock_timestamp()) where id=p_id;
    return found;
end;
$$;
create function public.byop_create_job(p_principal text,p_request jsonb,p_script text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare job public.content_jobs;
begin
    perform public.byop_assert_principal(p_principal);
    if p_request->>'generation_layout' is distinct from 'single_character'
        or lower(p_request->>'character') is distinct from 'ceo'
        or p_request->>'quantity' is distinct from '1' then raise exception 'CEO single character required'; end if;
    if p_script is null or length(btrim(p_script)) not between 1 and 4000 then raise exception 'Bounded script required'; end if;
    insert into public.content_jobs(idea,source,status,qa_status,byop_principal,script,content_package)
    values('CEO BYOP image','app_byop','ASSET_QUEUED','PENDING',p_principal,p_script,
        jsonb_build_object('byop_principal',p_principal,'asset_forge_request',p_request,
            'ceo_identity_required',true,'pipeline_route','VIDEO')) returning * into job;
    return to_jsonb(job);
end;
$$;
create function public.byop_job(p_principal text,p_id uuid) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
    perform public.byop_assert_principal(p_principal);
    select to_jsonb(j) into result from public.content_jobs j where id=p_id and byop_principal=p_principal for share;
    return result;
end;
$$;
create function public.byop_claim_execution(p_principal text,p_execution uuid,p_snapshot_hash text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare ledger public.byop_ledgers; execution jsonb; snap jsonb; credential jsonb; job jsonb; state jsonb;
begin
    perform public.byop_assert_principal(p_principal);
    select * into ledger from public.byop_ledgers where principal=p_principal for update;
    execution:=ledger.state->'executions'->p_execution::text;
    if execution is null or execution->>'state' is distinct from 'RESERVED'
        or execution->>'snapshot_sha256' is distinct from p_snapshot_hash
        or (execution->>'expires_at')::numeric<=extract(epoch from clock_timestamp()) then
        raise exception 'Execution absent, expired or already started';
    end if;
    snap:=execution->'snapshot';
    credential:=public.byop_credential(p_principal,(snap->>'credential_id')::uuid);
    if credential is null or credential->>'verification_status' is distinct from 'VERIFIED'
        or credential->'provider_ownership_verified' is distinct from 'true'::jsonb
        or credential->>'byop_revoked_at' is not null or credential->>'byop_verified_at' is null
        or credential->>'expires_at' is null
        or (credential->>'expires_at')::timestamptz<=clock_timestamp()
        or credential->>'provider_subject' is distinct from public.byop_expected_subject(p_principal) then
        raise exception 'Verified connected credential required';
    end if;
    -- Lock credential exclusively through dispatch claim; disconnect serializes
    -- before or after this durable boundary, never mutates another principal.
    perform 1 from public.pollinations_sessions where id=(snap->>'credential_id')::uuid for update;
    select to_jsonb(j) into job from public.content_jobs j where id=(snap->>'job_id')::uuid
        and byop_principal=p_principal for update;
    if job is null or job->>'status' is distinct from 'ASSET_QUEUED'
        or job->>'byop_revision' is distinct from snap->>'revision'
        or job->>'byop_model' is distinct from snap->>'model'
        or job->'content_package'->'asset_forge_request' is distinct from snap->'settings'->'request' then
        raise exception 'Job changed or already claimed';
    end if;
    execution:=execution||jsonb_build_object('state','CALL_STARTED','started_at',extract(epoch from clock_timestamp()));
    state:=jsonb_set(ledger.state,array['executions',p_execution::text],execution);
    if not public.byop_ledger_cas(p_principal,ledger.revision,state) then raise exception 'Ledger contention'; end if;
    update public.content_jobs set status='ASSET_GENERATING' where id=(snap->>'job_id')::uuid;
    return execution;
end;
$$;
create function public.byop_job_update(p_principal text,p_id uuid,p_revision bigint,p_action text,p_value jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare job public.content_jobs; package jsonb; sha text; decision text; next_status text;
begin
    perform public.byop_assert_principal(p_principal);
    select * into job from public.content_jobs where id=p_id and byop_principal=p_principal and byop_revision=p_revision for update;
    if not found then raise exception 'Job unavailable or changed'; end if;
    package:=job.content_package;
    if p_action='asset' then
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
revoke all on function public.byop_member_credential_immutable(),public.byop_job_binding_immutable(),
    public.byop_assert_principal(text),public.byop_expected_subject(text),public.byop_credential(text,uuid),
    public.byop_submit(text,text,text),public.byop_verify(text,uuid,text,boolean),public.byop_disconnect(text,uuid),
    public.byop_credentials(text),
    public.byop_create_job(text,jsonb,text),public.byop_job(text,uuid),public.byop_claim_execution(text,uuid,text),
    public.byop_job_update(text,uuid,bigint,text,jsonb) from public,anon,authenticated;
grant execute on function public.byop_assert_principal(text),public.byop_expected_subject(text),
    public.byop_credential(text,uuid),public.byop_submit(text,text,text),public.byop_verify(text,uuid,text,boolean),
    public.byop_credentials(text),
    public.byop_disconnect(text,uuid),public.byop_create_job(text,jsonb,text),public.byop_job(text,uuid),
    public.byop_claim_execution(text,uuid,text),public.byop_job_update(text,uuid,bigint,text,jsonb) to service_role;
grant select,insert,update on public.content_jobs to service_role;
-- Row locking needs an UPDATE privilege; do not grant membership activation.
grant update(updated_at) on public.soloforge_memberships to service_role;
commit;
