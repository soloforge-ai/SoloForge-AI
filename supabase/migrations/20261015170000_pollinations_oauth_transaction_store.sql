-- Shared OAuth transaction store. Additive only; do not apply to production in this PR.
-- No client DML. All operations require the backend service role.
create table if not exists public.pollinations_oauth_claims (
  kind text not null check (kind in ('login_ticket','pkce_state','mobile_handoff')),
  claim_hash text not null check (length(claim_hash) = 64),
  owner_user_id uuid not null references auth.users(id),
  payload jsonb not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  consumed_at timestamptz,
  primary key (kind, claim_hash)
);
alter table public.pollinations_oauth_claims enable row level security;
revoke all on public.pollinations_oauth_claims from public, anon, authenticated;
grant select, insert, update, delete on public.pollinations_oauth_claims to service_role;

-- Transaction payload may contain PKCE verifiers and handoff session identifiers.
-- Never expose it to clients, logs, or public views.
create or replace function public.pollinations_oauth_issue(
  p_kind text, p_claim_hash text, p_owner uuid, p_payload jsonb, p_expires_at timestamptz
) returns boolean language plpgsql security definer set search_path = '' as $$
begin
  if auth.role() is distinct from 'service_role'
     or p_kind not in ('login_ticket','pkce_state','mobile_handoff')
     or p_claim_hash !~ '^[0-9a-f]{64}$'
     or p_owner is null or p_payload is null
     or p_expires_at <= now() or p_expires_at > now() + interval '15 minutes' then
    raise exception 'OAuth transaction issue denied';
  end if;
  insert into public.pollinations_oauth_claims(kind,claim_hash,owner_user_id,payload,expires_at)
  values (p_kind,p_claim_hash,p_owner,p_payload,p_expires_at);
  return true;
end;
$$;

-- One UPDATE ... RETURNING is atomic across concurrent PostgreSQL connections.
-- Invalid, expired, previously consumed, or cross-owner claims return no payload.
create or replace function public.pollinations_oauth_consume(
  p_kind text, p_claim_hash text, p_owner uuid
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_payload jsonb;
begin
  if auth.role() is distinct from 'service_role'
     or p_kind not in ('login_ticket','pkce_state','mobile_handoff')
     or p_claim_hash !~ '^[0-9a-f]{64}$' or p_owner is null then
    raise exception 'OAuth transaction consume denied';
  end if;
  update public.pollinations_oauth_claims
     set consumed_at = now()
   where kind = p_kind and claim_hash = p_claim_hash
     and owner_user_id = p_owner and consumed_at is null and expires_at > now()
   returning payload into v_payload;
  return v_payload;
end;
$$;
revoke all on function public.pollinations_oauth_issue(text,text,uuid,jsonb,timestamptz) from public, anon, authenticated;
revoke all on function public.pollinations_oauth_consume(text,text,uuid) from public, anon, authenticated;
grant execute on function public.pollinations_oauth_issue(text,text,uuid,jsonb,timestamptz) to service_role;
grant execute on function public.pollinations_oauth_consume(text,text,uuid) to service_role;
