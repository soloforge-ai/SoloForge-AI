-- Additive V2 only. No seed values, legacy FKs, Auth users or provider calls.
-- Apply only under separate database authorization. Collisions fail, not overwrite.
begin;

create table public.soloforge_owners (
    owner_id uuid primary key check (owner_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    singleton boolean not null default true unique check (singleton),
    primary_email text not null unique check (
        primary_email = lower(btrim(primary_email)) and length(primary_email) <= 254
        and primary_email ~ '^[a-z0-9.!#$%&''*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}$'
    ),
    status text not null default 'active' check (status in ('active', 'disabled')),
    auth_epoch bigint not null default 0 check (auth_epoch >= 0),
    created_at timestamptz not null default clock_timestamp()
);

create table public.soloforge_owner_accounts (
    owner_id uuid not null references public.soloforge_owners(owner_id),
    provider text not null check (provider in ('supabase', 'render', 'pollinations')),
    provider_account_id text check (length(btrim(provider_account_id)) > 0),
    account_email text,
    verification_status text not null default 'pending'
        check (verification_status in ('pending', 'verified', 'mismatch')),
    verification_evidence text,
    verified_at timestamptz,
    primary key (owner_id, provider),
    check ((verification_status = 'verified' and provider_account_id is not null
        and verified_at is not null and length(btrim(verification_evidence)) > 0
        and verification_evidence is not null)
        or (verification_status <> 'verified' and verified_at is null))
);

create table public.owner_v2_challenges (
    challenge_id uuid primary key,
    owner_id uuid not null references public.soloforge_owners(owner_id),
    auth_epoch bigint not null,
    code_hash text not null check (code_hash ~ '^[0-9a-f]{64}$'),
    browser_hash text not null check (browser_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null,
    delivered_at timestamptz,
    consumed_at timestamptz,
    attempts integer not null default 0 check (attempts between 0 and 5)
);
create index owner_v2_challenges_owner_created on public.owner_v2_challenges(owner_id, created_at);

create table public.owner_v2_sessions (
    token_hash text primary key check (token_hash ~ '^[0-9a-f]{64}$'),
    owner_id uuid not null references public.soloforge_owners(owner_id),
    auth_epoch bigint not null,
    created_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null,
    revoked_at timestamptz
);

alter table public.soloforge_owners enable row level security;
alter table public.soloforge_owner_accounts enable row level security;
alter table public.owner_v2_challenges enable row level security;
alter table public.owner_v2_sessions enable row level security;
revoke all on public.soloforge_owners, public.soloforge_owner_accounts,
    public.owner_v2_challenges, public.owner_v2_sessions from public, anon, authenticated, service_role;
grant select on public.soloforge_owners, public.soloforge_owner_accounts to service_role;
-- UPDATE on one non-identity column permits row locks; monotonic epoch also permits
-- explicit administrative session revocation without changing owner identity.
grant update (auth_epoch) on public.soloforge_owners to service_role;
grant select, insert, update, delete on public.owner_v2_challenges, public.owner_v2_sessions to service_role;

create function public.owner_v2_lock_identity() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
    if tg_op = 'DELETE' then
        raise exception 'V2 owner identity is immutable';
    end if;
    if new.owner_id is distinct from old.owner_id
        or new.primary_email is distinct from old.primary_email
        or new.created_at is distinct from old.created_at
        or new.singleton is distinct from old.singleton then
        raise exception 'V2 owner identity is immutable';
    end if;
    if new.auth_epoch < old.auth_epoch then
        raise exception 'V2 auth epoch cannot decrease';
    end if;
    if new.status is distinct from old.status then
        new.auth_epoch := greatest(new.auth_epoch, old.auth_epoch + 1);
    end if;
    return new;
end;
$$;
revoke all on function public.owner_v2_lock_identity() from public, anon, authenticated, service_role;
create trigger owner_v2_immutable_identity before update or delete on public.soloforge_owners
    for each row execute function public.owner_v2_lock_identity();

-- Bootstrap is administrator-only, never a public/backend signup RPC. The owner
-- must confirm UUID/email separately. Known account IDs stay pending until evidence.
create function public.owner_v2_bootstrap(p_owner_id uuid, p_email text, p_accounts jsonb default '{}')
returns void language plpgsql security invoker set search_path = '' as $$
declare
    existing public.soloforge_owners%rowtype;
    provider_name text;
    account jsonb;
begin
    lock table public.soloforge_owners in exclusive mode;
    select * into existing from public.soloforge_owners;
    if existing.owner_id is not null then
        if existing.owner_id = p_owner_id and existing.primary_email = lower(btrim(p_email)) then
            return; -- Same seed is a no-op; never resets status, epoch or metadata.
        end if;
        raise exception 'V2 registry is already locked';
    end if;
    if p_accounts is null or jsonb_typeof(p_accounts) <> 'object'
        or exists (select 1 from jsonb_object_keys(p_accounts) k where k not in ('supabase','render','pollinations')) then
        raise exception 'Invalid V2 account metadata';
    end if;
    insert into public.soloforge_owners(owner_id, primary_email) values (p_owner_id, lower(btrim(p_email)));
    foreach provider_name in array array['supabase','render','pollinations'] loop
        account := coalesce(p_accounts -> provider_name, '{}');
        if jsonb_typeof(account) <> 'object'
            or exists (select 1 from jsonb_object_keys(account) k where k not in ('provider_account_id','account_email')) then
            raise exception 'Only confirmed account metadata is allowed';
        end if;
        insert into public.soloforge_owner_accounts(owner_id, provider, provider_account_id, account_email)
            values (p_owner_id, provider_name, nullif(btrim(account ->> 'provider_account_id'), ''),
                nullif(lower(btrim(account ->> 'account_email')), ''));
    end loop;
end;
$$;
revoke all on function public.owner_v2_bootstrap(uuid,text,jsonb) from public, anon, authenticated, service_role;

create function public.owner_v2_reserve_challenge(p_email text, p_challenge_id uuid, p_code_hash text, p_browser_hash text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    owner_row public.soloforge_owners%rowtype;
    instant timestamptz;
begin
    select * into owner_row from public.soloforge_owners where singleton for update;
    instant := clock_timestamp();
    if owner_row.owner_id is null or owner_row.status <> 'active' or owner_row.primary_email is distinct from p_email then
        return null;
    end if;
    if exists (select 1 from public.owner_v2_challenges where owner_id = owner_row.owner_id
        and created_at > instant - interval '60 seconds')
        or (select count(*) from public.owner_v2_challenges where owner_id = owner_row.owner_id
        and created_at > instant - interval '1 hour') >= 5 then return null; end if;
    delete from public.owner_v2_challenges where expires_at < instant - interval '1 day';
    delete from public.owner_v2_sessions where expires_at < instant - interval '1 day';
    insert into public.owner_v2_challenges(challenge_id, owner_id, auth_epoch, code_hash, browser_hash, created_at, expires_at)
        values(p_challenge_id, owner_row.owner_id, owner_row.auth_epoch, p_code_hash, p_browser_hash,
            instant, instant + interval '10 minutes');
    return jsonb_build_object('primary_email', owner_row.primary_email);
end;
$$;

create function public.owner_v2_activate_challenge(p_challenge_id uuid)
returns boolean language plpgsql security invoker set search_path = '' as $$
begin
    update public.owner_v2_challenges c set delivered_at = clock_timestamp()
    from public.soloforge_owners o where c.challenge_id = p_challenge_id and c.owner_id = o.owner_id
        and o.status = 'active' and c.auth_epoch = o.auth_epoch
        and c.delivered_at is null and c.consumed_at is null and c.expires_at > clock_timestamp();
    return found;
end;
$$;

create function public.owner_v2_consume_challenge(p_challenge_id uuid, p_browser_hash text, p_code_hash text, p_session_hash text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    owner_row public.soloforge_owners%rowtype;
    challenge public.owner_v2_challenges%rowtype;
    instant timestamptz;
begin
    select * into owner_row from public.soloforge_owners where singleton for update;
    select * into challenge from public.owner_v2_challenges where challenge_id = p_challenge_id for update;
    instant := clock_timestamp();
    if owner_row.owner_id is null or owner_row.status <> 'active'
        or challenge.owner_id is distinct from owner_row.owner_id
        or challenge.auth_epoch is distinct from owner_row.auth_epoch
        or challenge.delivered_at is null or challenge.consumed_at is not null
        or challenge.expires_at <= instant or challenge.attempts >= 5 then return null; end if;
    update public.owner_v2_challenges set attempts = attempts + 1 where challenge_id = p_challenge_id;
    if challenge.browser_hash is distinct from p_browser_hash or challenge.code_hash is distinct from p_code_hash then
        return null; -- Return, not raise: failed attempts must commit.
    end if;
    update public.owner_v2_challenges set consumed_at = instant where challenge_id = p_challenge_id;
    insert into public.owner_v2_sessions(token_hash, owner_id, auth_epoch, created_at, expires_at)
        values(p_session_hash, owner_row.owner_id, owner_row.auth_epoch, instant, instant + interval '1 hour');
    return jsonb_build_object('owner_id', owner_row.owner_id, 'primary_email', owner_row.primary_email, 'status', owner_row.status);
end;
$$;

create function public.owner_v2_session_identity(p_session_hash text)
returns jsonb language sql security invoker set search_path = '' as $$
    select jsonb_build_object('owner_id', o.owner_id, 'primary_email', o.primary_email, 'status', o.status)
    from public.owner_v2_sessions s join public.soloforge_owners o on o.owner_id = s.owner_id
    where s.token_hash = p_session_hash and s.revoked_at is null and s.expires_at > clock_timestamp()
        and o.status = 'active' and s.auth_epoch = o.auth_epoch;
$$;

create function public.owner_v2_revoke_session(p_session_hash text)
returns void language sql security invoker set search_path = '' as $$
    update public.owner_v2_sessions set revoked_at = clock_timestamp()
        where token_hash = p_session_hash and revoked_at is null;
$$;

revoke all on function public.owner_v2_reserve_challenge(text,uuid,text,text),
    public.owner_v2_activate_challenge(uuid), public.owner_v2_consume_challenge(uuid,text,text,text),
    public.owner_v2_session_identity(text), public.owner_v2_revoke_session(text) from public, anon, authenticated;
grant execute on function public.owner_v2_reserve_challenge(text,uuid,text,text),
    public.owner_v2_activate_challenge(uuid), public.owner_v2_consume_challenge(uuid,text,text,text),
    public.owner_v2_session_identity(text), public.owner_v2_revoke_session(text) to service_role;
commit;
