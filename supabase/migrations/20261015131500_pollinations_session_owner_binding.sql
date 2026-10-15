-- Additive schema only. Apply separately after review; do not deploy in this PR.
-- Existing ownerless sessions remain unusable by the owner-bound OAuth router.
alter table public.pollinations_sessions
  add column if not exists owner_user_id uuid references auth.users(id),
  add column if not exists provider_subject text;

-- Fail closed for new writes without owner and provider subject.
-- Existing rows are deliberately not backfilled or reassigned.
alter table public.pollinations_sessions
  add constraint pollinations_sessions_owner_subject_together
  check (
    (owner_user_id is null and provider_subject is null)
    or (owner_user_id is not null and provider_subject is not null and length(btrim(provider_subject)) > 0)
  );

comment on column public.pollinations_sessions.owner_user_id is
  'Verified SoloForge application owner from authenticated OAuth transaction; never client-supplied';
comment on column public.pollinations_sessions.provider_subject is
  'Verified Pollinations subject matching effective key userId';

-- Existing legacy rows remain untouched, but new inserts must be owner-bound.
-- The trigger complements the compatibility CHECK constraint without backfilling.
create or replace function public.reject_unbound_pollinations_session_insert()
returns trigger language plpgsql set search_path = '' as $$
begin
  if new.owner_user_id is null or new.provider_subject is null
     or length(btrim(new.provider_subject)) = 0 then
    raise check_violation using message = 'New Pollinations sessions require owner and provider subject';
  end if;
  return new;
end;
$$;

revoke all on function public.reject_unbound_pollinations_session_insert() from public;
create trigger pollinations_sessions_require_owner_on_insert
before insert on public.pollinations_sessions
for each row execute function public.reject_unbound_pollinations_session_insert();
