"""Repository-root alias for the deployed Pollinations OAuth router module."""

import sys
from backend.asset_forge.backend import pollinations_oauth_router as _impl

sys.modules[__name__] = _impl
