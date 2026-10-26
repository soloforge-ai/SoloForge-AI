"""Independent email-code authentication. No legacy identity or execution authority.

Opaque 256-bit email codes and sessions are stored as SHA256 digests. A separate
browser proof binds redemption to the client that requested the email. PostgreSQL
RPCs own expiry, rate limits and atomic consumption across application processes.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from uuid import UUID, uuid4

from .shared_supabase import supabase_request


class Unavailable(RuntimeError):
    """Fail closed without exposing infrastructure or secret details."""


class Unauthorized(ValueError):
    """Proof is absent, invalid, expired, consumed or revoked."""


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}", value):
        raise ValueError("Invalid email")
    return value


def require_enabled() -> None:
    if not (os.getenv("OWNER_V2_AUTH_ENABLED", "").strip().lower() == "true" or os.getenv("OWNER_V2_GITHUB_ENABLED", "").strip().lower() == "true"):
        raise Unavailable("Owner V2 is unavailable")


def rpc(name: str, body: dict) -> object:
    # Only fixed internal names are used; no client-selected tables/RPCs.
    try:
        return supabase_request("POST", f"rpc/owner_v2_{name}", body)
    except Exception:
        # No retries: a lost response can follow a committed consumption.
        raise Unavailable("Owner V2 is unavailable") from None


class SMTPDelivery:
    """V2-only SMTP over implicit TLS; never logs codes or retries delivery."""

    def __init__(self) -> None:
        try:
            self.host = os.environ["OWNER_V2_SMTP_HOST"].strip()
            self.port = int(os.getenv("OWNER_V2_SMTP_PORT", "465"))
            self.username = os.environ["OWNER_V2_SMTP_USERNAME"]
            self.password = os.environ["OWNER_V2_SMTP_PASSWORD"]
            self.sender = normalize_email(os.environ["OWNER_V2_SMTP_FROM"])
            if not self.host or not self.username or not self.password or not 1 <= self.port <= 65535:
                raise ValueError("Missing configuration")
        except (KeyError, ValueError):
            raise Unavailable("Owner V2 is unavailable") from None

    def send(self, email: str, code: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = normalize_email(email)
        message["Subject"] = "SoloForge Owner V2 sign-in code"
        message.set_content(
            "Use this one-time code only in the SoloForge sign-in screen where "
            "you requested it. It expires in 10 minutes.\n\n"
            f"{code}\n\nIf you did not request it, ignore this email. "
            "Signing in does not authorize spending or publishing.\n"
        )
        try:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=15, context=ssl.create_default_context()) as smtp:
                smtp.login(self.username, self.password)
                if smtp.send_message(message):
                    raise Unavailable("Owner V2 is unavailable")
        except Exception:
            raise Unavailable("Owner V2 is unavailable") from None


class OwnerV2:
    def __init__(self, call=rpc, delivery_factory=SMTPDelivery):
        self.call = call
        self.delivery_factory = delivery_factory

    def request(self, email: str) -> dict:
        require_enabled()
        email = normalize_email(email)
        delivery = self.delivery_factory()  # Validate settings before DB mutation.
        challenge_id = str(uuid4())
        browser_proof = secrets.token_urlsafe(32)
        code = secrets.token_urlsafe(32)
        row = self.call("reserve_challenge", {
            "p_email": email, "p_challenge_id": challenge_id,
            "p_code_hash": digest(code), "p_browser_hash": digest(browser_proof),
        })
        if row is not None:
            if not isinstance(row, dict) or row.get("primary_email") != email:
                raise Unavailable("Owner V2 is unavailable")
            # A failed/ambiguous delivery leaves a pending, unusable challenge.
            # Do not retry the send or activate it after a failure.
            delivery.send(email, code)
            if self.call("activate_challenge", {"p_challenge_id": challenge_id}) is not True:
                raise Unavailable("Owner V2 is unavailable")
        # Identical response for unknown email, inactive owner, or rate limiting.
        return {"accepted": True, "challenge_id": challenge_id,
                "browser_proof": browser_proof, "expires_in": 600}

    def verify(self, challenge_id: str, browser_proof: str, code: str) -> dict:
        require_enabled()
        try:
            challenge_id = str(UUID(challenge_id))
        except (ValueError, TypeError, AttributeError):
            raise Unauthorized("Invalid proof") from None
        if not all(isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", v) for v in (browser_proof, code)):
            raise Unauthorized("Invalid proof")
        session = "sf_owner_v2_" + secrets.token_urlsafe(32)
        row = self.call("consume_challenge", {
            "p_challenge_id": challenge_id, "p_browser_hash": digest(browser_proof),
            "p_code_hash": digest(code), "p_session_hash": digest(session),
        })
        identity = self._identity(row)
        return {**identity, "session_token": session, "token_type": "Bearer", "expires_in": 3600}

    @staticmethod
    def _identity(row: object) -> dict:
        if row is None:
            raise Unauthorized("Invalid proof")
        try:
            if not isinstance(row, dict) or row.get("status") != "active":
                raise ValueError("Invalid identity")
            owner_id = str(UUID(row["owner_id"]))
            email = normalize_email(row["primary_email"])
        except (KeyError, TypeError, ValueError, AttributeError):
            raise Unavailable("Owner V2 is unavailable") from None
        return {"owner_id": owner_id, "primary_email": email, "authenticated": True,
                "identity_version": "owner_v2"}

    @staticmethod
    def _session_hash(authorization: str | None) -> str:
        if not isinstance(authorization, str) or not re.fullmatch(r"Bearer sf_owner_v2_[A-Za-z0-9_-]{43}", authorization):
            raise Unauthorized("Invalid session")
        return digest(authorization[7:])

    def authenticate(self, authorization: str | None) -> dict:
        require_enabled()
        return self._identity(self.call("session_identity", {"p_session_hash": self._session_hash(authorization)}))

    def logout(self, authorization: str | None) -> None:
        require_enabled()
        self.call("revoke_session", {"p_session_hash": self._session_hash(authorization)})
