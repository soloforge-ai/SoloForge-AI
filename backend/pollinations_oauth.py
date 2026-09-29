"""Repository-root alias for the deployed Pollinations OAuth helper module."""

import sys
from backend.asset_forge.backend import pollinations_oauth as _impl

sys.modules[__name__] = _impl
