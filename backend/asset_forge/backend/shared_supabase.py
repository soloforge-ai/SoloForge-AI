"""Shared Supabase REST client for SoloForge backend modules.

This module owns the low-level authenticated REST request used by domain modules.
Keeping it here prevents content, publishing, sales, and routing code from
depending on Idea Flow internals.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def supabase_request(
    method: str,
    path: str,
    body: dict[str, object] | None = None,
    prefer: str | None = None,
    *,
    timeout: int = 15,
) -> Any:
    base_url = required_env("SUPABASE_URL").rstrip("/")
    secret_key = required_env("SUPABASE_SECRET_KEY")
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Accept": "application/json",
    }

    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if prefer:
        headers["Prefer"] = prefer

    request = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        # Avoid response bodies: Supabase diagnostics may contain private data.
        print("supabase_http_error", {"status": exc.code, "method": method})
        raise RuntimeError("SoloForge storage is unavailable") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            "supabase_transport_error",
            {"method": method, "exception_type": type(exc).__name__},
        )
        raise RuntimeError("SoloForge storage is unavailable") from exc

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("SoloForge storage returned an invalid response") from exc
