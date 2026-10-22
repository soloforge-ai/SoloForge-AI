"""Trusted PostgreSQL atomic owner binding. No credentials or grants stored.

Requires a dedicated trusted DB connection; never accepts a client-provided DSN.
The connection factory is injected for isolated testing. Production deployment
and migration application require separate authorization.
"""
from __future__ import annotations

import time
from backend.owner_provider_binding import BindingRejected, VerifiedIdentity, CredentialMetadata


class PostgresAtomicBindingStore:
    def __init__(self, connect):
        if not callable(connect):
            raise BindingRejected('Trusted PostgreSQL connection unavailable')
        self._connect = connect

    def verify_and_record(self, identity: VerifiedIdentity, key: CredentialMetadata, *,
                          authenticated_owner_id: str, now: int | None = None) -> None:
        now = int(time.time()) if now is None else now
        values = (identity.owner_user_id, identity.provider_account_id,
                  identity.internal_app_key_id, key.key_id, key.provider_account_id,
                  key.internal_app_key_id, authenticated_owner_id)
        if any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in values):
            raise BindingRejected('Missing identity evidence')
        if (identity.owner_user_id != authenticated_owner_id or
                key.provider_account_id != identity.provider_account_id or
                key.internal_app_key_id != identity.internal_app_key_id or
                type(now) is not int or type(key.expires_at) is not int or
                key.valid is not True or key.expires_at <= now):
            raise BindingRejected('Owner, application or key verification failed')

        # The owner row is the serialization point. ON CONFLICT cannot overwrite
        # immutable identity; SELECT verifies that the existing row is identical.
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''INSERT INTO public.owner_provider_bindings
                    (owner_user_id, provider_account_id, internal_app_key_id)
                    VALUES (%s::uuid, %s, %s) ON CONFLICT (owner_user_id) DO NOTHING''',
                    (authenticated_owner_id, identity.provider_account_id,
                     identity.internal_app_key_id))
                cur.execute('''SELECT provider_account_id, internal_app_key_id
                    FROM public.owner_provider_bindings
                    WHERE owner_user_id = %s::uuid FOR UPDATE''', (authenticated_owner_id,))
                row = cur.fetchone()
                if row != (identity.provider_account_id, identity.internal_app_key_id):
                    raise BindingRejected('Immutable owner binding mismatch')
                cur.execute('''INSERT INTO public.owner_provider_key_rotations
                    (owner_user_id, provider_key_id) VALUES (%s::uuid, %s)
                    ON CONFLICT (owner_user_id, provider_key_id) DO NOTHING''',
                    (authenticated_owner_id, key.key_id))
        # Commit is performed by the connection context manager only on success.
