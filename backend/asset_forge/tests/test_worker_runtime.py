from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ASSET_FORGE_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, filename: str):
    root = str(ASSET_FORGE_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    path = ASSET_FORGE_ROOT / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_runtime_registers_all_pipeline_loops() -> None:
    module = _load_module("soloforge_worker_runtime", "worker.py")
    names = [name for name, _ in module.WORKERS]

    assert names == [
        "content_generation",
        "content_router",
        "content_asset",
        "audio",
        "final_render",
        "publishing",
    ]


def test_embedded_worker_flag_defaults_to_enabled(monkeypatch) -> None:
    module = _load_module("soloforge_asset_forge_main_default", "main.py")
    monkeypatch.delenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", raising=False)
    assert module._embedded_workers_enabled() is True


def test_embedded_worker_flag_can_disable_web_pollers(monkeypatch) -> None:
    module = _load_module("soloforge_asset_forge_main_disabled", "main.py")
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "false")
    assert module._embedded_workers_enabled() is False
