"""Run the SoloForge Memory Foundation runtime test suite.

Usage from repository root:
    python backend/run_memory_tests.py

The runner discovers all backend tests whose filename starts with
``test_memory`` so Decision Memory, Memory Event, integration, and end-to-end
coverage share one repeatable execution command.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    backend_dir = Path(__file__).resolve().parent

    # Existing backend tests import local modules such as ``memory`` directly.
    # Put the backend directory first so the same command works from repo root.
    sys.path.insert(0, str(backend_dir))

    suite = unittest.defaultTestLoader.discover(
        start_dir=str(backend_dir),
        pattern="test_memory*.py",
    )

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
