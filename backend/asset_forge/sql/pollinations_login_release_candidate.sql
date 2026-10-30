-- Local release artifact only; NEVER auto-apply. One-time transactional migration.
-- Reuses the merged candidate verbatim after preflight. Reapplication fails safely.
-- Duplicate keys require explicit operator resolution; no rows are deleted or reassigned.
-- Local schema candidate only. NOT a production migration or authorization to apply.
-- Existing credential table must be inspected before staging/production adoption.
begin;
lock table public.pollinations_sessions in access exclusive mode;
do $preflight$
begin
    if exists (select 1 from public.pollinations_sessions group by access_token having count(*) > 1) then
        raise exception 'Duplicate credentials: resolve without deleting history before migration';
    end if;
    if exists (select 1 from information_schema.columns where table_schema='public'
        and table_name='pollinations_sessions' and column_name in
        ('submitted_by_owner','verification_status','provider_ownership_verified','spending_authorized','credential_digest')) then
        raise exception 'Already or partially migrated: inspect schema; do not replay';
    end if;
    if not exists (select 1 from pg_constraint where conrelid='public.pollinations_sessions'::regclass
        and conname='pollinations_sessions_owner_subject_together') then
        raise exception 'Unexpected legacy constraint: inspect schema';
    end if;
    if not exists (select 1 from pg_trigger where tgrelid='public.pollinations_sessions'::regclass
        and tgname='pollinations_sessions_require_owner_on_insert' and not tgisinternal) then
        raise exception 'Unexpected legacy insert guard: inspect schema';
    end if;
end;
$preflight$;

alter table public.pollinations_sessions
    add column submitted_by_owner uuid references public.soloforge_owners(owner_id),
    add column verification_status text not null default 'PENDING_VERIFICATION'
        check (verification_status in ('PENDING_VERIFICATION', 'VERIFIED')),
    add column provider_ownership_verified boolean not null default false,
    add column spending_authorized boolean not null default false check (not spending_authorized),
    add column credential_digest text generated always as
        (encode(sha256(access_token::bytea), 'hex')) stored,
    add constraint pollinations_binding_consistency check (
        (verification_status = 'VERIFIED' and provider_ownership_verified
            and submitted_by_owner is not null and length(btrim(provider_subject)) > 0
            and provider_subject is not null)
        or (verification_status = 'PENDING_VERIFICATION' and not provider_ownership_verified));
-- Preserve the legacy pair invariant while permitting independently verified V2 binding.
alter table public.pollinations_sessions drop constraint pollinations_sessions_owner_subject_together;
alter table public.pollinations_sessions add constraint pollinations_sessions_owner_subject_together check (
    (owner_user_id is null and provider_subject is null)
    or (owner_user_id is not null and provider_subject is not null and length(btrim(provider_subject)) > 0)
    or (submitted_by_owner is not null and verification_status='VERIFIED'
        and provider_ownership_verified and provider_subject is not null and length(btrim(provider_subject)) > 0));

-- Replace only this table's legacy INSERT trigger, retaining its bound legacy path.
create function public.pollinations_pending_insert_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
    if new.submitted_by_owner is not null and new.verification_status='PENDING_VERIFICATION'
        and not new.provider_ownership_verified and not new.spending_authorized
        and new.owner_user_id is null and new.provider_subject is null then
        return new;
    end if;
    if new.submitted_by_owner is null and new.owner_user_id is not null
        and new.provider_subject is not null and length(btrim(new.provider_subject)) > 0
        and new.verification_status='PENDING_VERIFICATION' and not new.provider_ownership_verified
        and not new.spending_authorized then
        return new;
    end if;
    raise check_violation using message='Authenticated owner submission required';
end;
$$;
revoke all on function public.pollinations_pending_insert_guard() from public, anon, authenticated;
drop trigger pollinations_sessions_require_owner_on_insert on public.pollinations_sessions;
create trigger pollinations_sessions_require_owner_on_insert before insert on public.pollinations_sessions
    for each row execute function public.pollinations_pending_insert_guard();

-- Duplicate existing credentials intentionally fail rather than silently reassign.
create unique index pollinations_credential_digest_unique on public.pollinations_sessions(credential_digest);
create index pollinations_owner_credentials on public.pollinations_sessions(submitted_by_owner);
alter table public.pollinations_sessions enable row level security;
revoke all on public.pollinations_sessions from public, anon, authenticated;
grant select, insert, update, delete on public.pollinations_sessions to service_role;

-- A record ID may never be recycled for a different secret or owner.
create function public.pollinations_credential_immutable() returns trigger
language plpgsql set search_path = '' as $$
begin
    if new.access_token is distinct from old.access_token
        or new.session_id is distinct from old.session_id
        or (old.submitted_by_owner is not null and new.submitted_by_owner is distinct from old.submitted_by_owner)
        or (old.submitted_by_owner is null and new.submitted_by_owner is not null
            and (new.verification_status <> 'PENDING_VERIFICATION' or new.provider_ownership_verified)) then
        raise exception 'Credential identity is immutable';
    end if;
    return new;
end;
$$;
revoke all on function public.pollinations_credential_immutable() from public, anon, authenticated;
create trigger pollinations_credential_immutable before update on public.pollinations_sessions
    for each row execute function public.pollinations_credential_immutable();

-- Recheck independent reference under lock at promotion time, after provider I/O.
create function public.pollinations_reverify(p_owner_id uuid, p_record_id uuid,
    p_subject text, p_identity_verified boolean) returns jsonb
language plpgsql security invoker set search_path = '' as $$
declare expected text; verified boolean := false; found_id uuid;
begin
    perform 1 from public.soloforge_owners where owner_id=p_owner_id and status='active' for update;
    if not found then return null; end if;
    select provider_account_id into expected from public.soloforge_owner_accounts
        where owner_id=p_owner_id and provider='pollinations' and verification_status='verified'
          and verified_at is not null and length(btrim(verification_evidence)) > 0;
    verified := coalesce(p_identity_verified and expected is not null and p_subject=expected, false);
    update public.pollinations_sessions set
        verification_status=case when verified then 'VERIFIED' else 'PENDING_VERIFICATION' end,
        provider_ownership_verified=verified,
        provider_subject=case when verified then p_subject when owner_user_id is not null then provider_subject else null end,
        spending_authorized=false
    where id=p_record_id and submitted_by_owner=p_owner_id and expires_at > clock_timestamp()
    returning id into found_id;
    if found_id is null then return null; end if;
    return jsonb_build_object('verification_status', case when verified then 'VERIFIED' else 'PENDING_VERIFICATION' end,
        'provider_ownership_verified', verified, 'provider_subject', case when verified then p_subject else null end,
        'spending_authorized', false);
end;
$$;
revoke all on function public.pollinations_reverify(uuid,uuid,text,boolean) from public, anon, authenticated;
grant execute on function public.pollinations_reverify(uuid,uuid,text,boolean) to service_role;
commit;
