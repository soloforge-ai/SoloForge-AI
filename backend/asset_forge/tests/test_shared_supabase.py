from __future__ import annotations

import json
from pathlib import Path

from backend.asset_forge.backend import shared_supabase


MIGRATED_MODULES = [
    "backend/asset_forge/backend/content_jobs_api.py",
    "backend/asset_forge/backend/content_router.py",
    "backend/asset_forge/backend/content_asset_generation.py",
    "backend/asset_forge/backend/publishing_api.py",
    "backend/asset_forge/backend/publora_publishing.py",
    "backend/asset_forge/backend/sales_inbox.py",
    "backend/asset_forge/backend/sales_sender.py",
    "backend/asset_forge/backend/content_generation.py",
    "backend/asset_forge/backend/audio_generation.py",
    "backend/asset_forge/backend/final_render.py",
]


def test_migrated_modules_do_not_depend_on_idea_flow_storage_helper() -> None:
    forbidden = (
        "from backend.idea_flow_webhook import _supabase_request",
        "from backend.asset_forge.backend.idea_flow_webhook import _supabase_request",
    )
    for relative_path in MIGRATED_MODULES:
        source = Path(relative_path).read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in source, f"{relative_path} still depends on Idea Flow storage"
        assert "def _supabase_request" not in source, (
            f"{relative_path} still defines a private Supabase REST client"
        )
        assert "from backend.shared_supabase import supabase_request as _supabase_request" in source


def test_shared_supabase_request_builds_authenticated_rest_request(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "service-secret")

    captured: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'[{"id":"job-1"}]'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(shared_supabase.urllib.request, "urlopen", fake_urlopen)

    result = shared_supabase.supabase_request(
        "POST",
        "content_jobs",
        body={"status": "NEW"},
        prefer="return=representation",
    )

    assert result == [{"id": "job-1"}]
    assert captured["url"] == "https://example.supabase.co/rest/v1/content_jobs"
    assert captured["method"] == "POST"
    assert json.loads(captured["body"].decode("utf-8")) == {"status": "NEW"}
    headers = {str(k).lower(): v for k, v in captured["headers"].items()}
    assert headers["apikey"] == "service-secret"
    assert headers["authorization"] == "Bearer service-secret"
    assert headers["prefer"] == "return=representation"
