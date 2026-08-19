# SoloForge × Pollinations BYOP OAuth

## Phase 2 scope

This branch adds the server-side OAuth 2.1 + PKCE building blocks for Pollinations Bring Your Own Pollen (BYOP). It does **not** change Asset Forge generation yet.

Pollinations recommends the authorization-code flow with PKCE for new web integrations. The flow uses the publishable App Key (`pk_...`) as `client_id`, returns a short-lived authorization code to the exact registered callback, and exchanges that code for a scoped user key (`sk_...`).

## Runtime configuration

Set these values in the Render service environment (never commit them):

```text
POLLINATIONS_CLIENT_ID=pk_...
POLLINATIONS_REDIRECT_URI=https://soloforge-asset-forge.onrender.com/auth/pollinations/callback
```

Optional overrides:

```text
POLLINATIONS_AUTHORIZE_URL=https://enter.pollinations.ai/authorize
POLLINATIONS_TOKEN_URL=https://enter.pollinations.ai/api/oauth/token
POLLINATIONS_OAUTH_SCOPE=profile usage
POLLINATIONS_SESSION_COOKIE_SECURE=true
```

The `pk_...` App Key is publishable. The user-authorized `sk_...` token is sensitive and must not be committed, logged, placed in URLs, analytics, cookies, or long-lived browser storage.

## Flow

```text
GET /auth/pollinations/login
        |
        | generate verifier + S256 challenge + state
        v
Pollinations /authorize
        |
        | user signs in + consents
        v
GET /auth/pollinations/callback?code=...&state=...
        |
        | validate state
        | exchange code + verifier
        v
Pollinations /api/oauth/token
        |
        v
scoped sk_...
        |
        v
short-lived authenticated session
```

## Integration boundary

`backend/pollinations_oauth.py` is framework-neutral. `backend/pollinations_oauth_router.py` provides the FastAPI transport layer. The actual Asset Forge FastAPI application must mount `router` before the Render callback can work.

## Security requirements

- Validate the callback `state` before exchanging the code.
- Use the exact Redirect URI registered on the Pollinations App Key.
- Use PKCE S256 with a fresh verifier for every transaction.
- Never expose `sk_...` in logs, query strings, analytics, source control, cookies, or client bundles.
- Do not reuse an authorization code or PKCE verifier.
- Keep the user token in a short-lived secure server-side session.
- The current MVP session store is in-memory; introduce a shared encrypted session store before horizontal scaling.
- Do not replace the current server-owned image key yet. Asset Forge will be migrated to BYOP only after the OAuth route is integrated and tested.

## Acceptance test

1. Open `/auth/pollinations/login`.
2. Approve the Pollinations consent screen.
3. Confirm the callback succeeds without exposing `sk_...`.
4. Confirm `/auth/pollinations/status` reports `connected: true` without the token.
5. Confirm logout returns `connected: false`.
6. Confirm Asset Forge generation is still unchanged.
