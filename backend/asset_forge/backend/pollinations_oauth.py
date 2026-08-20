"""Pollinations BYOP OAuth 2.1 + PKCE helpers for SoloForge."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_AUTHORIZE_URL = "https://enter.pollinations.ai/authorize"
DEFAULT_TOKEN_URL = "https://enter.pollinations.ai/api/oauth/token"
DEFAULT_SCOPE = "profile usage"
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PollinationsOAuthConfig:
    client_id: str
    redirect_uri: str
    authorize_url: str = DEFAULT_AUTHORIZE_URL
    token_url: str = DEFAULT_TOKEN_URL
    scope: str = DEFAULT_SCOPE

    @classmethod
    def from_env(cls) -> "PollinationsOAuthConfig":
        client_id = os.getenv("POLLINATIONS_CLIENT_ID", "").strip()
        redirect_uri = os.getenv("POLLINATIONS_REDIRECT_URI", "").strip()
        if not client_id:
            raise RuntimeError("POLLINATIONS_CLIENT_ID is not configured")
        if not redirect_uri:
            raise RuntimeError("POLLINATIONS_REDIRECT_URI is not configured")
        return cls(
            client_id=client_id,
            redirect_uri=redirect_uri,
            authorize_url=os.getenv("POLLINATIONS_AUTHORIZE_URL", DEFAULT_AUTHORIZE_URL).strip(),
            token_url=os.getenv("POLLINATIONS_TOKEN_URL", DEFAULT_TOKEN_URL).strip(),
            scope=os.getenv("POLLINATIONS_OAUTH_SCOPE", DEFAULT_SCOPE).strip(),
        )


def _base64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_pkce_transaction() -> tuple[str, str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = _base64url_sha256(verifier)
    state = secrets.token_urlsafe(32)
    return verifier, challenge, state


def build_authorization_url(
    config: PollinationsOAuthConfig,
    *,
    code_challenge: str,
    state: str,
    models: str | None = None,
    budget: int | float | None = None,
    expiry_days: int | None = None,
) -> str:
    if not state:
        raise ValueError("state is required")
    if not code_challenge:
        raise ValueError("code_challenge is required")
    params: dict[str, Any] = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if models:
        params["models"] = models
    if budget is not None:
        params["budget"] = budget
    if expiry_days is not None:
        params["expiry"] = expiry_days
    return f"{config.authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_authorization_code(
    config: PollinationsOAuthConfig,
    *,
    code: str,
    code_verifier: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not code:
        raise ValueError("code is required")
    if not code_verifier:
        raise ValueError("code_verifier is required")
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "code_verifier": code_verifier,
    }).encode("utf-8")
    request = urllib.request.Request(
        config.token_url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "SoloForge-Pollinations-OAuth/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Pollinations OAuth token endpoint is unavailable") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Pollinations token endpoint returned non-JSON") from exc
    if status < 200 or status >= 300:
        error = payload.get("error", "token_exchange_failed")
        description = payload.get("error_description", "")
        detail = f": {description}" if description else ""
        raise RuntimeError(f"Pollinations OAuth error: {error}{detail}")
    if not payload.get("access_token"):
        raise RuntimeError("Pollinations token response has no access_token")
    return payload
