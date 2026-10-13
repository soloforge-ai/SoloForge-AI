"""MVP publishing isolation: no Publora dispatch without a future owner-approved policy.

This intentionally has no environment-variable bypass. Keep existing job records
and publishing code for future migration/reconciliation, but do not call Publora.
"""
from __future__ import annotations

from fastapi import HTTPException


def require_publishing_enabled() -> None:
    raise HTTPException(
        status_code=503,
        detail="External publishing is disabled in the SoloForge MVP. Export content locally.",
    )
