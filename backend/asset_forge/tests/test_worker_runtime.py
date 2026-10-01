from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_worker_module():
    path = Path(__file__).resolve().parents[1] / "worker.py"
    spec = importlib.util.spec_from_file_location("soloforge_worker_runtime", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_runtime_registers_all_pipeline_loops() -> None:
    module = _load_worker_module()
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
    import main

    monkeypatch.delenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", raising=False)
    assert main._embedded_workers_enabled() is True


def test_embedded_worker_flag_can_disable_web_pollers(monkeypatch) -> None:
    import main

    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "false")
    assert main._embedded_workers_enabled() is False
