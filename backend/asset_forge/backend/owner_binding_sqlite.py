"""Local-only atomic owner binding for disposable offline OAuth tests.

Not a production persistence adapter. No secrets or spending grants are stored.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from backend.owner_provider_binding import BindingRejected, VerifiedIdentity, CredentialMetadata


class LocalAtomicBindingStore:
    def __init__(self, path: str):
        if not path or path == ':memory:':
            raise BindingRejected('A durable disposable database path is required')
        self.path = str(Path(path).resolve())
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS owner_bindings (
                owner_id TEXT PRIMARY KEY, account_id TEXT NOT NULL,
                app_id TEXT NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS key_rotations (
                owner_id TEXT NOT NULL, key_id TEXT NOT NULL,
                PRIMARY KEY(owner_id,key_id),
                FOREIGN KEY(owner_id) REFERENCES owner_bindings(owner_id))''')

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
                not key.valid or key.expires_at <= now):
            raise BindingRejected('Owner, application or key verification failed')
        with sqlite3.connect(self.path, timeout=5, isolation_level=None) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            try:
                db.execute('INSERT OR IGNORE INTO owner_bindings VALUES (?,?,?)',
                           (identity.owner_user_id, identity.provider_account_id,
                            identity.internal_app_key_id))
                existing = db.execute('SELECT account_id,app_id FROM owner_bindings WHERE owner_id=?',
                                      (authenticated_owner_id,)).fetchone()
                if existing != (identity.provider_account_id, identity.internal_app_key_id):
                    raise BindingRejected('Immutable owner binding mismatch')
                db.execute('INSERT OR IGNORE INTO key_rotations VALUES (?,?)',
                           (authenticated_owner_id, key.key_id))
                db.execute('COMMIT')
            except Exception:
                db.execute('ROLLBACK')
                raise
