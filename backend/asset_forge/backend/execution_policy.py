"""S1 execution controls. Process enablement is never spending authorization.

Generation stays locked until trusted owner, approval and budget evidence can
be verified independently. No environment variable or request flag unlocks it.
"""
from __future__ import annotations

import os
from fastapi import HTTPException


def explicitly_enabled(name: str) -> bool:
    """Only documented true values enable a process; all others fail closed."""
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def generation_execution_authorized() -> bool:
    # S1 does not implement the missing owner/wallet/approval/budget verifier.
    return False


def interactive_chat_execution_authorized() -> bool:
    """Interactive chat requires its own trusted spending authorization (not implemented in S1)."""
    return False


def require_interactive_chat_execution() -> None:
    if not interactive_chat_execution_authorized():
        raise HTTPException(
            status_code=503,
            detail="Interactive chat is locked pending verified owner and spending authorization.",
        )


def require_generation_execution() -> None:
    from .byop_pilot import check_gate
    if check_gate():
        return
    if not generation_execution_authorized():
        raise HTTPException(
            status_code=503,
            detail="Generation execution is locked pending verified owner and spending authorization.",
        )
