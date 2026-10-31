-- Atomic owner-binding repair. Callable only by backend service_role.
-- Requires prior Owner V2 authentication and live Pollinations userinfo match in backend.
-- Does not grant direct UPDATE on owner registry or authorize spending.
begin;
create function public.pollinations_bind_and_reverify(
    p_owner_id uuid, p_record_id uuid, p_subject text
) returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare
    bound_id uuid;
    credential_id uuid;
begin
    if p_owner_id is null or p_record_id is null or p_subject is null
       or length(btrim(p_subject)) = 0 or length(p_subject) > 512
       or position('sk_' in p_subject) > 0 or position('Bearer ' in p_subject) > 0 then
        return null;
    end if;
    perform 1 from public.soloforge_owners
        where owner_id = p_owner_id and status = 'active' for update;
    if not found then return null; end if;
    -- Lock credential before account promotion. No first-subject auto-claim.
    perform 1 from public.pollinations_sessions
        where id = p_record_id and submitted_by_owner = p_owner_id
          and expires_at > clock_timestamp() for update;
    if not found then return null; end if;
    update public.soloforge_owner_accounts set
        provider_account_id = p_subject,
        verification_status = 'verified',
        verification_evidence = 'owner_v2_configured_subject_sk_userinfo_v1',
        verified_at = clock_timestamp()
    where owner_id = p_owner_id and provider = 'pollinations'
      and verification_status = 'pending' and provider_account_id is null
      and verification_evidence is null and verified_at is null
    returning owner_id into bound_id;
    if bound_id is null then return null; end if;
    update public.pollinations_sessions set
        verification_status = 'VERIFIED',
        provider_ownership_verified = true,
        provider_subject = p_subject,
        spending_authorized = false
    where id = p_record_id and submitted_by_owner = p_owner_id
      and expires_at > clock_timestamp()
    returning id into credential_id;
    if credential_id is null then
        raise exception 'Credential changed during owner binding';
    end if;
    return jsonb_build_object(
        'verification_status','VERIFIED',
        'provider_ownership_verified',true,
        'provider_subject',p_subject,
        'spending_authorized',false
    );
end;
$$;
revoke all on function public.pollinations_bind_and_reverify(uuid,uuid,text)
    from public, anon, authenticated;
grant execute on function public.pollinations_bind_and_reverify(uuid,uuid,text)
    to service_role;
commit;
