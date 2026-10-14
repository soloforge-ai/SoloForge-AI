"""S1 tests: real closed policy, fake credentials, no external services."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import socket
import sys
from types import ModuleType
from unittest.mock import Mock
import urllib.request

from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient
import pytest

from backend import execution_policy as policy
from backend.asset_forge.backend import (
    asset_provider, audio_generation, combined_telegram_webhook as telegram,
    content_asset_generation, content_generation, content_jobs_api as jobs,
    content_router, final_render, prawtwan_chat, sales_inbox,
)

ROOT = Path(__file__).resolve().parents[1]


def load_runtime(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("Network forbidden"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("HTTP forbidden"))
    for name in ("SOLOFORGE_RUN_EMBEDDED_WORKERS", "SOLOFORGE_RUN_DEDICATED_WORKERS"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("value", [None, "", " ", "false", "0", "no", "off", "tru", "enabled", "2", "true,false"])
def test_disabled_embedded_startup(monkeypatch, value, capsys):
    main = load_runtime("s1_main_disabled", "main.py")
    if value is not None:
        monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", value)
    create_task = Mock()
    monkeypatch.setattr(main.asyncio, "create_task", create_task)
    asyncio.run(main.start_content_workers())
    create_task.assert_not_called()
    assert capsys.readouterr().out == "embedded_content_workers_disabled\n"


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", " TRUE "])
def test_explicit_embedded_startup_is_mocked_only(monkeypatch, value):
    main = load_runtime("s1_main_enabled", "main.py")
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", value)
    calls = []
    def fake_create(coro):
        calls.append(coro.cr_code.co_name)
        coro.close()  # Never run any real loop.
    monkeypatch.setattr(main.asyncio, "create_task", fake_create)
    asyncio.run(main.start_content_workers())
    assert len(calls) == 6
    assert policy.generation_execution_authorized() is False


@pytest.mark.parametrize("value", [None, "", "false", "enabled", "invalid"])
def test_dedicated_disabled_even_if_embedded_enabled(monkeypatch, value, capsys):
    worker = load_runtime("s1_worker_disabled", "worker.py")
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "true")
    if value is not None:
        monkeypatch.setenv("SOLOFORGE_RUN_DEDICATED_WORKERS", value)
    create_task = Mock()
    monkeypatch.setattr(worker.asyncio, "create_task", create_task)
    asyncio.run(worker.run_background_workers())
    create_task.assert_not_called()
    assert capsys.readouterr().out == "dedicated_content_workers_disabled\n"


def test_dedicated_explicit_enablement_runs_only_fake_loops(monkeypatch):
    worker = load_runtime("s1_worker_enabled", "worker.py")
    monkeypatch.setenv("SOLOFORGE_RUN_DEDICATED_WORKERS", "true")
    calls = []
    async def fake_worker():
        calls.append("started")
    class ImmediateStop:
        def set(self): pass
        async def wait(self): await asyncio.sleep(0)
    monkeypatch.setattr(worker, "WORKERS", tuple((str(i), fake_worker) for i in range(6)))
    monkeypatch.setattr(worker.asyncio, "Event", ImmediateStop)
    async def run():
        monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler", lambda *a: None)
        await worker.run_background_workers()
    asyncio.run(run())
    assert len(calls) == 6


@pytest.mark.parametrize("module,func,arg,result", [
    (content_generation, "process_selected_job", "j", False),
    (content_generation, "process_selected_once", None, 0),
    (content_asset_generation, "process_asset_job", "j", False),
    (content_asset_generation, "process_assets_once", None, 0),
    (audio_generation, "process_video_asset_job", "j", False),
    (audio_generation, "process_video_assets_once", None, 0),
    (final_render, "process_audio_ready_job", "j", False),
    (final_render, "process_audio_ready_once", None, 0),
    (content_router, "route_approved_job", "j", None),
    (content_router, "process_approved_routes_once", None, 0),
])
def test_no_backlog_claim_or_mutation(monkeypatch, module, func, arg, result):
    database = Mock(side_effect=AssertionError("No claim/read/write allowed"))
    monkeypatch.setattr(module, "_supabase_request", database)
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "true")
    monkeypatch.setenv("SOLOFORGE_RUN_DEDICATED_WORKERS", "true")
    assert getattr(module, func)(*(() if arg is None else (arg,))) == result
    database.assert_not_called()


@pytest.mark.parametrize("action,status", [("approve", "READY_FOR_REVIEW"), ("continue", "APPROVED"), ("regenerate", "READY_FOR_REVIEW"), ("create", "BACKLOG")])
def test_api_repeated_concurrent_denial_preserves_job(monkeypatch, action, status):
    original = {"id": "j", "status": status, "qa_status": "PENDING", "retry_count": 2,
                "hook": "existing draft", "content_package": {}}
    monkeypatch.setattr(jobs, "_require_session", lambda _: None)
    monkeypatch.setattr(jobs, "_get_row", lambda _: dict(original))
    database = Mock(side_effect=AssertionError("No mutation allowed"))
    provider = Mock()
    monkeypatch.setattr(jobs, "_supabase_request", database)
    monkeypatch.setattr(jobs, "process_selected_job", provider)
    def call(_):
        tasks = BackgroundTasks()
        with pytest.raises(HTTPException) as error:
            if action == "create":
                jobs.create_from_idea(jobs.IdeaCreateRequest(idea="valid idea", recommendation_id="personal_post"), tasks, None)
            else:
                getattr(jobs, action + "_content_job")("j", tasks, None)
        assert error.value.status_code == 503
        assert tasks.tasks == []
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(call, range(24)))
    database.assert_not_called()
    provider.assert_not_called()
    assert original["status"] == status and original["retry_count"] == 2
    assert original["hook"] == "existing draft"


def test_authentication_not_bypassed(monkeypatch):
    def deny(_): raise HTTPException(status_code=401, detail="Unauthorized")
    monkeypatch.setattr(jobs, "_require_session", deny)
    read = Mock()
    monkeypatch.setattr(jobs, "_get_row", read)
    with pytest.raises(HTTPException) as error:
        jobs.continue_content_job("j", BackgroundTasks(), None)
    assert error.value.status_code == 401
    read.assert_not_called()


@pytest.mark.parametrize("func,args", [(jobs._resume_job, ("j", "ASSET_READY")), (jobs._continue_approved_job, ("j",))])
def test_background_helpers_cannot_bypass(monkeypatch, func, args):
    provider = Mock()
    monkeypatch.setattr(jobs, "process_asset_job", provider)
    monkeypatch.setattr(jobs, "process_video_asset_job", provider)
    with pytest.raises(HTTPException): func(*args)
    provider.assert_not_called()


def test_telegram_resume_is_truthfully_blocked(monkeypatch):
    class Service:
        def get_content_job(self, _): return {"id": "j", "status": "APPROVED", "content_package": {}}
    monkeypatch.setattr(telegram, "SupabaseIdeaFlowService", Service)
    tasks = BackgroundTasks()
    with pytest.raises(HTTPException) as error:
        telegram._content_callback("content:continue:j", background_tasks=tasks)
    assert error.value.status_code == 503 and tasks.tasks == []


def test_direct_boundaries_cannot_bypass(monkeypatch):
    main = load_runtime("s1_main_boundary", "main.py")
    provider = Mock(side_effect=AssertionError("Provider must not dispatch"))
    monkeypatch.setattr(urllib.request, "urlopen", provider)
    # This retained root adapter is outside Docker dependencies; fake its transport.
    transport = ModuleType("requests")
    transport.get = provider
    monkeypatch.setitem(sys.modules, "requests", transport)
    monkeypatch.syspath_prepend(str(ROOT.parents[0]))
    pollinations_image = load_runtime("s1_root_image", "../pollinations_image.py")
    monkeypatch.setattr(pollinations_image, "requests", transport)
    monkeypatch.setattr(prawtwan_chat, "get_pollinations_access_token_from_authorization", lambda _: "fake-test-only")
    calls = [
        lambda: main._generate_sheet("p", b"reference", "fake-test-only"),
        lambda: content_generation._call_provider("idea"),
        lambda: asset_provider._pollinations_image("p"),
        lambda: asset_provider.generate_asset("p", fallback_title="title"),
        lambda: pollinations_image.generate_image({"prompt": "p"}),
        lambda: prawtwan_chat.chat_with_prawtwan(prawtwan_chat.PrawtwanChatRequest(messages=[{"role": "user", "content": "Hi"}]), None),
    ]
    for call in calls:
        with pytest.raises(HTTPException) as error: call()
        assert error.value.status_code == 503
    provider.assert_not_called()


@pytest.mark.parametrize("layout", ["single_character", "sticker_sheet"])
def test_asset_api_does_not_treat_connected_oauth_as_spending_approval(monkeypatch, layout):
    main = load_runtime("s1_main_api", "main.py")
    provider = Mock()
    monkeypatch.setattr(main, "get_pollinations_access_token_from_authorization", lambda _: "fake-test-only")
    monkeypatch.setattr(main, "_generate_sheet", provider)
    payload = {"quantity": 4} if layout == "sticker_sheet" else {"generation_layout": layout, "quantity": 1, "pose_intent": "presenting", "expression": "calm"}
    client = TestClient(main.app)
    for _ in range(3):
        response = client.post("/v1/asset-forge/generate", json=payload)
        assert response.status_code == 503
        assert "fake-test-only" not in response.text
    provider.assert_not_called()


def test_read_only_routes_and_local_sales_template_remain_safe(monkeypatch):
    main = load_runtime("s1_main_read", "main.py")
    client = TestClient(main.app)
    assert client.get("/health").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    sessions = Mock()
    monkeypatch.setattr(jobs, "_require_session", sessions)
    monkeypatch.setattr(jobs, "_supabase_request", lambda *a, **k: [{"id": "j", "status": "READY_FOR_REVIEW"}])
    assert jobs.list_content_jobs(limit=10, authorization="fake-test-only")["items"][0]["status"] == "READY_FOR_REVIEW"
    sessions.assert_called_once_with("fake-test-only")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-only")
    assert sales_inbox.draft_outreach({"company": "Test"})["body"]


def test_legacy_offline_sheet_remains_explicitly_local(monkeypatch):
    main = load_runtime("s1_main_offline", "main.py")
    provider = Mock()
    monkeypatch.setattr(main, "get_pollinations_access_token_from_authorization", lambda _: None)
    monkeypatch.setattr(main, "_load_character_reference", lambda _: None)
    monkeypatch.setattr(main, "_generate_sheet", provider)
    response = TestClient(main.app).post("/v1/asset-forge/generate", json={"character": "Cat", "quantity": 4})
    assert response.status_code == 200
    assert response.json()["generation_mode"] == "local_fallback"
    provider.assert_not_called()


def test_flags_and_credential_presence_cannot_unlock_generation(monkeypatch):
    for name in ("SOLOFORGE_RUN_EMBEDDED_WORKERS", "SOLOFORGE_RUN_DEDICATED_WORKERS", "SOLOFORGE_ALLOW_AUTOMATIC_EXECUTION", "POLLINATIONS_TEXT_ENABLED"):
        monkeypatch.setenv(name, "true")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "fake-test-only")
    assert policy.generation_execution_authorized() is False
    with pytest.raises(HTTPException) as error:
        policy.require_generation_execution()
    assert error.value.status_code == 503


def test_generate_on_create_denied_before_any_database_write_or_dispatch(monkeypatch):
    """A connected session alone must not create a SELECTED job or queue generation."""
    monkeypatch.setattr(jobs, "_require_session", lambda _: None)
    database = Mock(side_effect=AssertionError("No DB operation before spending authorization"))
    provider = Mock(side_effect=AssertionError("No provider call allowed"))
    monkeypatch.setattr(jobs, "_supabase_request", database)
    monkeypatch.setattr(jobs, "process_selected_job", provider)
    tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as error:
        jobs.create_from_idea(
            jobs.IdeaCreateRequest(
                idea="A valid content idea",
                recommendation_id="personal_post",
                action="generate",
            ),
            tasks,
            "Bearer fake-session",
        )

    assert error.value.status_code == 503
    assert tasks.tasks == []
    database.assert_not_called()
    provider.assert_not_called()


def test_generate_on_create_default_action_also_denied_before_dispatch(monkeypatch):
    """Omitting action defaults to generate and must never bypass S1."""
    monkeypatch.setattr(jobs, "_require_session", lambda _: None)
    database = Mock(side_effect=AssertionError("No DB mutation allowed"))
    monkeypatch.setattr(jobs, "_supabase_request", database)
    tasks = BackgroundTasks()
    request = jobs.IdeaCreateRequest(idea="Another valid idea", recommendation_id="personal_post")
    assert request.action == "generate"

    with pytest.raises(HTTPException) as error:
        jobs.create_from_idea(request, tasks, "Bearer fake-session")

    assert error.value.status_code == 503
    assert tasks.tasks == []
    database.assert_not_called()
