# SoloForge owner authentication rollout

Status: draft in RUJ Batch A. Do not merge or deploy without owner approval.

## Verified owner identity

Read-only query on 2026-10-04 in Supabase project `dhazxwfzaccrttckuylw`:
`auth.users.id = 72112ead-d399-4a40-aa51-ee17811cb10d`,
`is_anonymous = false`, and a linked `auth.identities` row with
`provider = github`, `provider_id = 304932313` and GitHub login
`soloforge-ai`. This is the account that owns the SoloForge repository.
The email and provider token are not used for authorization.

## Security behavior

The backend validates a Supabase bearer with `/auth/v1/user` and requires
the exact server-side owner UUID plus GitHub in trusted `app_metadata.providers`.
Anonymous sign-in, another GitHub user, and legacy Pollinations exchange cannot
obtain owner sessions. Unbound v1 sessions are rejected. v2 app sessions expire
after 15 minutes by default (maximum 1 hour); renewal requires a fresh
Supabase owner bearer. Existing mobile GitHub sessions persist via the
Supabase Flutter SDK. The publishable key is safe for a client; all service
keys and OAuth client secrets remain server-side.

## Deployment gate and lockout recovery

1. Confirm GitHub provider and `soloforge://oauth/supabase` redirect are enabled.
2. Keep the working GitHub login on the owner's Android device. Install a
   full-flow candidate APK and verify backend bootstrap, Content Queue, app
   restart, and a fresh GitHub sign-in before considering production rollout.
3. Set `SOLOFORGE_OWNER_USER_ID` on Render to the verified UUID above, or
   use the code default. Confirm `SUPABASE_PUBLISHABLE_KEY` and
   `SOLOFORGE_SESSION_SECRET` exist on Render without printing their values.
4. Deploy backend and compatible app together only after owner approval.
   The backend immediately rejects old v1 sessions. The owner can recover
   by signing in with GitHub again; the client obtains a new v2 session.
5. If the owner GitHub identity must change, verify the replacement in
   `auth.users` and `auth.identities` first, then change only the server-side
   `SOLOFORGE_OWNER_USER_ID`. The APK never carries an owner allowlist.
6. To revoke every issued app session, rotate `SOLOFORGE_SESSION_SECRET` or
   set `SOLOFORGE_SESSION_NOT_BEFORE` to a Unix timestamp later than their
   issuance. A stolen app bearer remains usable until its 15-minute expiry
   unless one of these controls is applied.

Supabase anonymous sign-in may remain enabled for unrelated flows, but it
cannot authorize private SoloForge APIs after this rollout.
Pollinations remains an optional generation provider, not an auth gate.
