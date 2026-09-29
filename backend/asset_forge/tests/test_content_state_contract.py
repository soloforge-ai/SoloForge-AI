from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from backend.asset_forge.backend import content_generation
from backend.asset_forge.backend.content_state import CONTENT_JOB_STATUSES


MIGRATION = Path("supabase/migrations/202609280001_content_ops_v3.sql")
CORE_STATUS_FILES = [
    Path("backend/asset_forge/backend/content_generation.py"),
    Path("backend/asset_forge/backend/content_router.py"),
    Path("backend/asset_forge/backend/content_asset_generation.py"),
    Path("backend/asset_forge/backend/audio_generation.py"),
    Path("backend/asset_forge/backend/final_render.py"),
    Path("backend/asset_forge/backend/publishing_api.py"),
    Path("backend/asset_forge/backend/publora_publishing.py"),
]


def _migration_statuses() -> set[str]:
    source = MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        r"add constraint content_jobs_status_check\s+check \(status in \((.*?)\)\);",
        source,
        re.S,
    )
    assert match is not None, "content_jobs_status_check was not found"
    return set(re.findall(r"'([A-Z_]+)'", match.group(1)))


def test_state_contract_matches_database_constraint() -> None:
    assert _migration_statuses() == set(CONTENT_JOB_STATUSES)


def test_core_workers_only_write_known_content_job_statuses() -> None:
    observed: set[str] = set()
    auxiliary_status_literals = {"PASS", "BLOCKED"}
    for path in CORE_STATUS_FILES:
        source = path.read_text(encoding="utf-8")
        observed.update(re.findall(r'status=eq\.([A-Z_]+)', source))
        observed.update(re.findall(r'"status"\s*:\s*"([A-Z_]+)"', source))
    assert observed
    assert observed <= set(CONTENT_JOB_STATUSES) | auxiliary_status_literals


def test_generation_finish_persists_generated_at(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append({
            "method": method,
            "path": path,
            "body": body,
            "prefer": prefer,
        })
        return [{"id": "job-1"}]

    monkeypatch.setattr(content_generation, "_supabase_request", fake_request)

    content_generation._finish_job(
        {
            "id": "job-1",
            "content_package": {"content_id": "C001"},
        },
        {
            "hook": "Hook",
            "script": "Script",
            "caption": "Caption",
            "cta": "CTA",
            "onscreen_text": [],
            "visual_prompt": "Visual",
            "motion_prompt": "",
            "risk_level": "LOW",
        },
        "test-provider",
        "test-model",
    )

    assert len(calls) == 1
    body = calls[0]["body"]
    assert isinstance(body, dict)
    generated_at = body.get("generated_at")
    assert isinstance(generated_at, str)
    parsed = datetime.fromisoformat(generated_at)
    assert parsed.tzinfo is not None
    assert body["status"] == "READY_FOR_REVIEW"


def test_repository_pollinations_imports_resolve_to_deployed_files() -> None:
    import backend.pollinations_oauth as root_oauth
    import backend.pollinations_oauth_router as root_router
    from backend.asset_forge.backend import pollinations_oauth as deployed_oauth
    from backend.asset_forge.backend import pollinations_oauth_router as deployed_router

    assert Path(root_oauth.__file__).resolve() == Path(deployed_oauth.__file__).resolve()
    assert Path(root_router.__file__).resolve() == Path(deployed_router.__file__).resolve()
