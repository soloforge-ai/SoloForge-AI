# Pollinations BYOP OAuth — Phase 2C

Phase 2C integrates the Phase 2B OAuth/PKCE layer into the actual Asset Forge FastAPI service.

## Runtime routes

- `GET /auth/pollinations/login`
- `GET /auth/pollinations/callback`
- `GET /auth/pollinations/status`
- `POST /auth/pollinations/logout`
- Existing `/health` and `/v1/asset-forge/generate` remain unchanged.

The Asset Forge application includes the OAuth router with FastAPI `app.include_router(...)`, so the OAuth endpoints are part of the same deployed API surface. FastAPI documents this as the standard multi-file router integration pattern.

## Environment

```text
POLLINATIONS_CLIENT_ID=pk_...
POLLINATIONS_REDIRECT_URI=https://soloforge-asset-forge.onrender.com/auth/pollinations/callback
POLLINATIONS_SESSION_COOKIE_SECURE=true
```

No user `sk_...` token is added to Render environment variables.

## Important boundary

Asset Forge image generation still uses the existing `POLLINATIONS_API_KEY`. Phase 2C only proves the OAuth transport/session boundary. BYOP-funded generation is a later phase after live OAuth validation.

## Session limitation

The MVP session store is in-memory. Restarting the Render instance invalidates connected sessions, and multiple instances would not share sessions. Before horizontal scaling, replace it with a shared encrypted session store.

## Deployment status

This branch is code-only. Render has **not** been deployed as part of Phase 2C.
