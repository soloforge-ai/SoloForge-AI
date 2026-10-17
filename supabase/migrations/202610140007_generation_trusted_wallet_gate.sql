-- Security hardening: deliberately fail closed pending a trusted provider verifier.
-- The attestation authority is NOT service_role. No provider verification is
-- performed by this migration; real wallet spending remains disabled.
begin;
create schema if not exists generation_trust;
revoke all on schema generation_trust from public,anon,authenticated,service_role;
create table generation_trust.wallet_attestations(
 budget_account_id uuid primary key references public.generation_budget_accounts(id) on delete restrict,
 owner_user_id uuid not null references auth.users(id) on delete restrict,
 pollinations_session_id text not null references public.pollinations_sessions(session_id) on delete restrict,
 wallet_fingerprint text not null check(wallet_fingerprint ~ '^[0-9a-f]{64}$'),
 wallet_category text not null check(wallet_category in ('QUEST','PAID')),
 authorization_ref text not null check(length(btrim(authorization_ref))>0),
 allocation_ref text not null check(length(btrim(allocation_ref))>0),
 max_authorized_pollen numeric(20,8) not null check(max_authorized_pollen>0),
 verified_at timestamptz not null,
 expires_at timestamptz not null check(expires_at>verified_at),
 revoked_at timestamptz,
 evidence_sha256 text not null check(evidence_sha256 ~ '^[0-9a-f]{64}$')
);
revoke all on generation_trust.wallet_attestations from public,anon,authenticated,service_role;
alter table generation_trust.wallet_attestations enable row level security;
alter table generation_trust.wallet_attestations force row level security;
-- Only migration/DB owner can provision records after independent provider verification.
-- Service role can never mint, read, or update attestations.
create or replace function generation_trust.check_wallet(
 p_account uuid,p_owner uuid,p_session text,p_fingerprint text,
 p_category text,p_allocation text,p_amount numeric
) returns boolean language sql security definer
set search_path='' as $$
 select exists (
  select 1 from generation_trust.wallet_attestations a
  where a.budget_account_id=p_account and a.owner_user_id=p_owner
  and a.pollinations_session_id=p_session and a.wallet_fingerprint=p_fingerprint
  and a.wallet_category=p_category and a.allocation_ref=p_allocation
  and a.revoked_at is null and a.verified_at<=clock_timestamp()
  and a.expires_at>clock_timestamp() and a.max_authorized_pollen>=p_amount
 )
$$;
revoke all on function generation_trust.check_wallet(uuid,uuid,text,text,text,text,numeric) from public,anon,authenticated,service_role;
grant usage on schema generation_trust to service_role;
grant execute on function generation_trust.check_wallet(uuid,uuid,text,text,text,text,numeric) to service_role;
commit;
