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
