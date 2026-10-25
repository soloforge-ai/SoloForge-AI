-- Additive bridge: no account seeding or automatic provider verification.
begin;
create function public.owner_v2_github_session(p_supabase_user_id uuid, p_session_hash text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare matched public.soloforge_owners%rowtype; instant timestamptz;
begin
    if p_session_hash !~ '^[0-9a-f]{64}$' then return null; end if;
    select o.* into matched from public.soloforge_owners o
      join public.soloforge_owner_accounts a on a.owner_id=o.owner_id
      where o.singleton and o.status='active'
        and a.provider='supabase' and a.verification_status='verified'
        and a.provider_account_id=p_supabase_user_id::text
        and a.verified_at is not null and a.verification_evidence is not null
      for update of o;
    if matched.owner_id is null then return null; end if;
    instant := clock_timestamp();
    insert into public.owner_v2_sessions(token_hash,owner_id,auth_epoch,created_at,expires_at)
      values(p_session_hash,matched.owner_id,matched.auth_epoch,instant,instant+interval '1 hour');
    return jsonb_build_object('owner_id',matched.owner_id,'primary_email',matched.primary_email,'status',matched.status);
end;
$$;
revoke all on function public.owner_v2_github_session(uuid,text) from public,anon,authenticated;
grant execute on function public.owner_v2_github_session(uuid,text) to service_role;
commit;
