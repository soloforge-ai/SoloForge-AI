# Pollinations BYOP OAuth — Phase 2B

## Scope

Phase 2B adds the FastAPI OAuth transport layer around the Phase 2 PKCE helpers.

### Routes

- `GET /auth/pollinations/login`
  - Generates a fresh PKCE verifier/challenge and CSRF state.
  - Redirects to Pollinations `/authorize`.
- `GET /auth/pollinations/callback`
  - Validates and consumes the one-time state.
  - Exchanges the authorization code server-side.
  - Stores the resulting user-scoped `sk_...` token only in the server-side session store.
  - Never returns the token in the callback URL or status response.
- `GET /auth/pollinations/status`
  - Returns connection state, expiry, and granted scope only.
- `POST /auth/pollinations/logout`
  - Invalidates the server session and clears the browser cookie.

## Session security

The browser receives only an opaque `__Host-soloforge_session` cookie. The cookie is configured as `HttpOnly`, `SameSite=Lax`, and `Secure` by default. The actual Pollinations access token stays server-side.

This implementation intentionally uses an in-memory store for the MVP. A restart or multi-instance deployment will invalidate sessions; a shared encrypted session store should be introduced before horizontal scaling.

## Environment

```text
POLLINATIONS_CLIENT_ID=pk_...
POLLINATIONS_REDIRECT_URI=https://soloforge-asset-forge.onrender.com/auth/pollinations/callback
POLLINATIONS_SESSION_COOKIE_SECURE=true
```

`POLLINATIONS_CLIENT_ID` is the publishable App Key (`pk_...`). It is not a user secret. Do not place a user `sk_...` in Render environment variables for BYOP.

## Integration boundary

`backend/pollinations_oauth_router.py` is intentionally reusable. The Asset Forge FastAPI application should mount `router` when the OAuth branch is combined with the Asset Forge service branch. The existing image-generation path continues using `POLLINATIONS_API_KEY` until BYOP generation is explicitly validated.

## Security invariants

1. `state` is required and single-use.
2. PKCE uses S256.
3. Authorization codes are exchanged server-side.
4. `sk_...` is never placed in a URL, cookie value, API response, log message, or source file.
5. Session IDs are high-entropy opaque values.
6. OAuth transactions expire after 10 minutes.
7. User sessions expire with the Pollinations token expiry.
