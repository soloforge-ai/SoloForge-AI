"""Repository-root compatibility shim for Pollinations OAuth routes.

The deployed Asset Forge Docker image imports the implementation from
backend/asset_forge/backend. Repository-root tests and local development should
exercise that same implementation rather than a shadow copy.
"""

from backend.asset_forge.backend.pollinations_oauth_router import *  # noqa: F401,F403
