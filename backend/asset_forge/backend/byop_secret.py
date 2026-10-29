"""Explicitly injected AEAD keyring; no environment/default keys or network.

Requires cryptography in the selected runtime. Never persist the keyring with DB
rows. A fresh object with the retained keyring can read existing ciphertext.
"""
import base64
import json
import secrets


class SecretBox:
    def __init__(self, keys, active):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if active not in keys or any(not isinstance(k, str) or not isinstance(v, bytes) or len(v) != 32 for k, v in keys.items()):
            raise ValueError('Explicit 256-bit keyring required')
        self._keys = {k: AESGCM(v) for k, v in keys.items()}
        self.active = active

    @staticmethod
    def aad(principal, account, credential_id):
        return json.dumps(['v1', principal, 'cloudflare', account, credential_id], separators=(',', ':')).encode()

    def encrypt(self, token, principal, account, credential_id):
        nonce = secrets.token_bytes(12)
        data = self._keys[self.active].encrypt(nonce, token.encode(), self.aad(principal, account, credential_id))
        return self.active, base64.b64encode(nonce + data).decode()

    def decrypt(self, key_id, ciphertext, principal, account, credential_id):
        try:
            data = base64.b64decode(ciphertext, validate=True)
            return self._keys[key_id].decrypt(data[:12], data[12:], self.aad(principal, account, credential_id)).decode()
        except Exception:
            raise ValueError('Credential decryption unavailable') from None
