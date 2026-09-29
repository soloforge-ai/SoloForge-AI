"""Repository-root compatibility shim for Pollinations OAuth helpers.

The deployed Asset Forge Docker image uses backend/asset_forge/backend as its
backend package. Keep that implementation canonical and make repository-root
imports resolve to the same code during tests and local development.
"""

from backend.asset_forge.backend.pollinations_oauth import *  # noqa: F401,F403
