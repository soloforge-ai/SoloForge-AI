"""Offline Content Job -> real CEO contracts -> mocked provider/storage.

The provider returns the approved master as a fixture, not new AI artwork.
No environment flag unlocks generation; authorization is substituted in tests only.
"""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import socket
import math
import struct
import wave
import urllib.request
from urllib.parse import parse_qs, urlsplit
from datetime import datetime, timezone

from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend import (
    asset_provider, content_asset_generation as assets, content_jobs_api,
    execution_policy, publora_publishing, publishing_api, content_router, final_render,
)
import runtime

forge = runtime.asset_forge_main
MASTER = Path(__file__).resolve().parents[3] / "frontend/assets/characters/ceo/references/master.png"
REQUEST = {
    "character": "CEO", "generation_layout": "single_character", "quantity": 1,
    "pose_intent": "presenting", "expression": "calm",
    "wardrobe_variant": "creator", "campaign_id": "manifest_glow_lab",
}


@pytest.fixture
def offline(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("External I/O or worker dispatch forbidden in offline CEO proof")

    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "false")
    monkeypatch.setenv("SOLOFORGE_RUN_DEDICATED_WORKERS", "false")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "offline-test-only")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    for name in ("content_worker_loop", "content_router_loop", "content_asset_worker_loop",
                 "audio_worker_loop", "final_render_worker_loop", "publishing_worker_loop"):
        monkeypatch.setattr(forge, name, forbidden)
    monkeypatch.setattr(asset_provider, "_pollinations_image", forbidden)
    monkeypatch.setattr(asset_provider, "_template_image", forbidden)
    monkeypatch.setattr(forge, "_generate_local_fallback_sheet", forbidden)
    monkeypatch.setattr(forge, "_load_character_reference", lambda _: MASTER.read_bytes())
    state = {
        "job": {"id": "offline-ceo-job", "idea": "Creator workflow tips",
                "status": "ASSET_QUEUED", "retry_count": 0,
                "content_package": {"pipeline_route": "VISUAL", "goal": "education",
                                    "asset_forge_request": deepcopy(REQUEST)}},
        "transitions": [], "provider_calls": [], "uploads": [],
    }

    def database(method, path, body=None, prefer=None):
        assert path.startswith("content_jobs?")
        query = parse_qs(urlsplit(path).query)
        if "content_package" in query:
            expected = json.loads(query["content_package"][0].removeprefix("eq."))
            if expected != state["job"]["content_package"]:
                return []
        if "status=eq." in path:
            required = path.split("status=eq.")[1].split("&")[0]
            if state["job"]["status"] != required:
                return []
        if method == "GET":
            return [deepcopy(state["job"])]
        assert method == "PATCH"
        state["job"].update(deepcopy(body))
        state["transitions"].append(body["status"])
        return [deepcopy(state["job"])]

    def upload(data, path):
        state["uploads"].append(path)
        (tmp_path / "cover.png").write_bytes(data)

    def provider(prompt, reference, token):
        assert token == "offline-test-only"
        assert hashlib.sha256(reference).hexdigest() == forge.CEO_MASTER_SHA256
        assert "APPROVED CHARACTER DNA" in prompt
        assert "Glasses are mandatory" in prompt
        assert "NEVER show teeth" in prompt
        assert "No wings, halo" in prompt
        assert forge.CEO_OUTFITS["default"] in prompt
        assert forge.CEO_OUTFITS["creator"] not in prompt
        state["provider_calls"].append(prompt)
        return MASTER.read_bytes()

    monkeypatch.setattr(assets, "_supabase_request", database)
    monkeypatch.setattr(content_jobs_api, "_supabase_request", database)
    monkeypatch.setattr(assets, "_upload_asset", upload)
    monkeypatch.setattr(forge, "_generate_sheet", provider)
    state["evidence_dir"] = tmp_path
    return state


def authorize_mock_only(monkeypatch):
    monkeypatch.setattr(assets, "generation_execution_authorized", lambda: True)
    monkeypatch.setattr(asset_provider, "require_generation_execution", lambda: None)
    monkeypatch.setattr(forge, "require_generation_execution", lambda: None)


def test_content_job_mock_ceo_attachment_and_review_output(offline, monkeypatch):
    authorize_mock_only(monkeypatch)
    assert assets.process_asset_job("offline-ceo-job") is True
    job = offline["job"]
    package = job["content_package"]
    assert offline["transitions"] == ["ASSET_GENERATING", "READY_FOR_REVIEW"]
    assert len(offline["provider_calls"]) == 1
    assert offline["uploads"] == [f"offline-ceo-job/{package['asset_sha256']}.png"]
    assert package["asset_storage_path"] == offline["uploads"][0]
    assert package["asset_count"] == 1 and package["asset_status"] == "READY"
    assert package["brand_applied"] is True
    assert package["asset_review_status"] == "PENDING"
    # Exercise the existing review preview contract without issuing signed-URL I/O.
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(content_jobs_api, "_get_row", lambda _: deepcopy(job))
    def signed_url(bucket, path):
        assert bucket == "content-assets" and path == package["asset_storage_path"]
        return "https://offline.invalid/cover.png"
    monkeypatch.setattr(publora_publishing, "_signed_storage_url", signed_url)
    monkeypatch.setattr(content_jobs_api, "_signed_storage_url", signed_url)
    assert content_jobs_api.get_asset_preview(job["id"], "offline-session") == {
        "url": "https://offline.invalid/cover.png", "media_type": "image",
        "asset_status": "READY", "pipeline_route": "VISUAL",
        "asset_sha256": package["asset_sha256"],
    }
    manifest = package["asset_forge_manifest"]
    assert manifest["reference_sha256"] == forge.CEO_MASTER_SHA256
    assert manifest["character"] == "CEO" and manifest["quantity"] == 1
    assert manifest["effective_wardrobe"] == "default"
    assert manifest["generation_layout"] == "single_character"
    assert manifest["source_sha256"] == hashlib.sha256(MASTER.read_bytes()).hexdigest()
    with Image.open(offline["evidence_dir"] / "cover.png") as result:
        with Image.open(BytesIO(MASTER.read_bytes())) as master:
            assert result.size == master.size
        assert result.format == "PNG"
    # A second explicit processing request cannot claim or regenerate this job.
    assert assets.process_asset_job("offline-ceo-job") is False
    assert len(offline["provider_calls"]) == 1
    (offline["evidence_dir"] / "job.json").write_text(json.dumps(job, indent=2))
    print(f"Mock-only review artifact: {offline['evidence_dir']}")


@pytest.mark.parametrize("failure", ["timeout", "bad_image", "missing_master", "bad_master",
                                     "invalid_request", "null_request", "product_conflict",
                                     "missing_credential", "upload"])
def test_ceo_failures_stop_without_fallback_or_retry(offline, monkeypatch, failure):
    authorize_mock_only(monkeypatch)
    package = offline["job"]["content_package"]
    if failure in {"timeout", "bad_image"}:
        def failed_provider(*args):
            offline["provider_calls"].append("failed")
            if failure == "timeout":
                raise HTTPException(504, "private-provider-detail")
            return b"invalid-image"
        monkeypatch.setattr(forge, "_generate_sheet", failed_provider)
    elif failure in {"missing_master", "bad_master"}:
        monkeypatch.setattr(forge, "_load_character_reference",
                            lambda _: None if failure == "missing_master" else b"bad")
    elif failure == "invalid_request":
        package["asset_forge_request"]["quantity"] = 4
    elif failure == "null_request":
        package["asset_forge_request"] = None
    elif failure == "product_conflict":
        package["goal"] = "conversion"
    elif failure == "missing_credential":
        monkeypatch.delenv("POLLINATIONS_API_KEY")
    elif failure == "upload":
        def failed_upload(*args):
            raise RuntimeError("Asset upload failed")
        monkeypatch.setattr(assets, "_upload_asset", failed_upload)
    assert assets.process_asset_job("offline-ceo-job") is False
    assert offline["job"]["status"] == "ASSET_FAILED"
    assert offline["job"]["content_package"]["asset_status"] == "FAILED"
    assert offline["job"]["retry_count"] == 1
    assert len(offline["provider_calls"]) == (1 if failure in {"timeout", "bad_image", "upload"} else 0)
    assert offline["uploads"] == []
    assert "private-provider-detail" not in offline["job"]["error_message"]
    assert assets.process_asset_job("offline-ceo-job") is False


def test_real_execution_lock_prevents_claim_and_provider(offline):
    assert execution_policy.generation_execution_authorized() is False
    assert assets.process_asset_job("offline-ceo-job") is False
    assert assets.process_assets_once() == 0
    with pytest.raises(HTTPException) as error:
        asset_provider.generate_asset("ignored", fallback_title="CEO", asset_forge_request=REQUEST)
    assert error.value.status_code == 503
    with pytest.raises(HTTPException) as error:
        forge.build_asset_pack(forge.AssetForgeRequest(**REQUEST), access_token="offline-test-only")
    assert error.value.status_code == 503
    assert offline["transitions"] == [] and offline["provider_calls"] == []


def test_existing_api_wrapper_reuses_pack_contract(offline, monkeypatch):
    authorize_mock_only(monkeypatch)
    monkeypatch.setattr(forge, "get_pollinations_access_token_from_authorization",
                        lambda _: "offline-test-only")
    result = forge.generate_asset_pack(forge.AssetForgeRequest(**REQUEST), "offline-session")
    assert isinstance(result, forge.AssetForgeResponse)
    assert result.generation_layout == "single_character"
    assert result.output_manifest["reference_sha256"] == forge.CEO_MASTER_SHA256
    assert len(result.files) == 1 and len(offline["provider_calls"]) == 1


@pytest.mark.parametrize("decision", ["APPROVED", "REJECTED"])
@pytest.mark.parametrize("route", ["VISUAL", "VIDEO"])
def test_http_review_is_required_and_bound_to_current_image(offline, monkeypatch, decision, route):
    authorize_mock_only(monkeypatch)
    offline["job"]["content_package"]["pipeline_route"] = route
    assert assets.process_asset_job("offline-ceo-job")
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    url = "/v1/content-jobs/offline-ceo-job/asset-review"
    digest = offline["job"]["content_package"]["asset_sha256"]
    assert digest == hashlib.sha256((offline["evidence_dir"] / "cover.png").read_bytes()).hexdigest()
    stale = client.post(url, json={"decision": decision, "asset_sha256": "0" * 64})
    assert stale.status_code == 409
    assert client.post(url, json={"decision": "PASS", "asset_sha256": digest}).status_code == 422
    # Existing content approval must not bypass asset review or schedule work.
    assert client.post("/v1/content-jobs/offline-ceo-job/approve").status_code == 409
    result = client.post(url, json={"decision": decision, "asset_sha256": digest})
    assert result.status_code == 200, result.text
    job = result.json()
    assert job["content_package"]["asset_review_status"] == decision
    if decision == "REJECTED":
        assert job["status"] == "READY_FOR_REVIEW" and job["qa_status"] == "FAIL"
        with pytest.raises(ValueError):
            asset_provider.require_ceo_asset_review(job["content_package"])
    else:
        assert job["status"] == ("ASSET_READY" if route == "VIDEO" else "READY_TO_PUBLISH")
        asset_provider.require_ceo_asset_review(job["content_package"])
        assert client.post(url, json={"decision": decision, "asset_sha256": digest}).status_code == 409
    assert len(offline["provider_calls"]) == 1


def test_review_requires_authentication_and_atomic_current_package(offline, monkeypatch):
    offline["job"].update(status="READY_FOR_REVIEW")
    package = offline["job"]["content_package"]
    package.update(asset_status="READY", asset_storage_path="j/cover.png", asset_sha256="a" * 64)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    def deny(_):
        raise HTTPException(401, "Unauthorized")
    monkeypatch.setattr(content_jobs_api, "_require_session", deny)
    url = "/v1/content-jobs/offline-ceo-job/asset-review"
    payload = {"decision": "APPROVED", "asset_sha256": "a" * 64}
    assert client.post(url, json=payload).status_code == 401
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    stale = deepcopy(offline["job"])
    monkeypatch.setattr(content_jobs_api, "_get_row", lambda _: deepcopy(stale))
    package["asset_sha256"] = "b" * 64  # Replacement after the request snapshot.
    assert client.post(url, json=payload).status_code == 409
    assert offline["transitions"] == []


@pytest.mark.parametrize("review", [None, "PENDING", "REJECTED", "APPROVED"])
def test_pending_rejected_or_stale_review_cannot_publish_or_route(offline, monkeypatch, review):
    def forbidden(*args, **kwargs):
        pytest.fail("Unreviewed CEO image reached publishing I/O")
    package = offline["job"]["content_package"]
    package.update(asset_status="READY", asset_storage_path="j/cover.png", asset_sha256="a" * 64,
                   asset_review_status=review, asset_review_sha256="b" * 64)
    # Even a legacy/mis-stated READY_TO_PUBLISH row must fail before account I/O.
    offline["job"]["status"] = "READY_TO_PUBLISH"
    monkeypatch.setattr(publishing_api, "require_publishing_enabled", lambda: None)
    monkeypatch.setattr(publishing_api, "_get_job", lambda _: deepcopy(offline["job"]))
    monkeypatch.setattr(publishing_api, "_require_session", lambda _: None)
    monkeypatch.setattr(publishing_api, "list_connections", forbidden)
    monkeypatch.setattr(publishing_api, "_supabase_request", forbidden)
    monkeypatch.setattr(publora_publishing, "list_connections", forbidden)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    assert client.post("/v1/publishing/offline-ceo-job/publish-now", json={}).status_code == 400
    assert client.post("/v1/publishing/offline-ceo-job/schedule", json={
        "scheduled_time": "2099-01-01T00:00:00Z"}).status_code == 400
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        publishing_api._claim_submission(offline["job"], platform_ids=[], scheduled_time=now)
    with pytest.raises(ValueError):
        publora_publishing.submit_to_publora(offline["job"], platform_ids=[], scheduled_time=now)
    with pytest.raises(ValueError):
        content_router._route_approved_row(offline["job"])
    captured = []
    monkeypatch.setattr(final_render, "_supabase_request", lambda *a, **k: captured.append(k["body"]))
    with pytest.raises(asset_provider.CharacterAssetError):
        final_render._finish(offline["job"], "j/video.mp4", {})
    assert captured == []


@pytest.mark.parametrize("route,expected", [("personal_post", "READY_TO_PUBLISH"),
                                           ("carousel", "ASSET_QUEUED"),
                                           ("short_video", "ASSET_QUEUED")])
def test_unrelated_routing_is_preserved(offline, monkeypatch, route, expected):
    captured = []
    monkeypatch.setattr(content_router, "_supabase_request",
                        lambda *a, **k: captured.append(k["body"]) or [k["body"]])
    content_router._route_approved_row({"id": "ordinary", "content_package": {"format": route}})
    assert captured[0]["status"] == expected
    asset_provider.require_ceo_asset_review({})


def test_approved_ceo_reuses_asset_without_regeneration(offline, monkeypatch):
    package = offline["job"]["content_package"]
    package.update(asset_status="READY", asset_storage_path="j/cover.png", asset_sha256="a" * 64,
                   asset_review_status="APPROVED", asset_review_sha256="a" * 64)
    captured = []
    monkeypatch.setattr(content_router, "_supabase_request",
                        lambda *a, **k: captured.append(k["body"]) or [k["body"]])
    content_router._route_approved_row(offline["job"])
    assert captured[0]["status"] == "READY_TO_PUBLISH"
    assert offline["provider_calls"] == []


@pytest.mark.parametrize("semantic", ["STALE", "FAIL"])
def test_asset_approval_preserves_content_semantic_gate(offline, monkeypatch, semantic):
    offline["job"]["status"] = "READY_FOR_REVIEW"
    offline["job"]["content_package"].update(
        asset_status="READY", asset_storage_path="j/cover.png", asset_sha256="a" * 64,
        semantic_fidelity={"status": semantic})
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    result = client.post("/v1/content-jobs/offline-ceo-job/asset-review",
                         json={"decision": "APPROVED", "asset_sha256": "a" * 64})
    assert result.status_code == 409
    assert offline["transitions"] == []


def test_regeneration_invalidates_old_image_and_review(offline, monkeypatch):
    offline["job"].update(status="READY_FOR_REVIEW", video_storage_path="old/video.mp4", render_status="READY")
    offline["job"]["content_package"].update(
        asset_status="READY", asset_storage_path="old/cover.png", asset_sha256="a" * 64,
        asset_review_status="REJECTED", asset_review_sha256="a" * 64)
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(content_jobs_api, "require_generation_execution", lambda: None)
    tasks = BackgroundTasks()  # Capture only; never execute generation.
    result = content_jobs_api.regenerate_content_job("offline-ceo-job", tasks, "offline")
    package = result["content_package"]
    assert package["asset_forge_request"] == REQUEST
    assert "asset_storage_path" not in package and "asset_review_status" not in package
    assert result["video_storage_path"] is None and result["render_status"] is None
    with pytest.raises(ValueError):
        asset_provider.require_ceo_asset_review(package)
    assert len(tasks.tasks) == 1 and offline["provider_calls"] == []


def test_legacy_pending_render_without_provenance_cannot_be_released(offline, monkeypatch):
    offline["job"].update(status="READY_FOR_REVIEW", video_storage_path="j/video.mp4", render_status="READY")
    offline["job"]["content_package"].update(
        pipeline_route="VIDEO", asset_status="READY", asset_storage_path="j/cover.png", asset_sha256="a" * 64)
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    result = client.post("/v1/content-jobs/offline-ceo-job/asset-review",
                         json={"decision": "APPROVED", "asset_sha256": "a" * 64})
    assert result.status_code == 409 and offline["job"]["status"] == "READY_FOR_REVIEW"
    assert offline["provider_calls"] == []


def test_video_pending_image_preview_returns_current_hash(offline, monkeypatch):
    authorize_mock_only(monkeypatch)
    offline["job"]["content_package"]["pipeline_route"] = "VIDEO"
    assert assets.process_asset_job("offline-ceo-job")
    package = offline["job"]["content_package"]
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    def signed(bucket, path):
        assert bucket == "content-assets" and path == package["asset_storage_path"]
        return "https://offline.invalid/current.png"
    monkeypatch.setattr(content_jobs_api, "_signed_storage_url", signed)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    result = client.get("/v1/content-jobs/offline-ceo-job/asset-preview")
    assert result.status_code == 200
    assert result.json()["media_type"] == "image"
    assert result.json()["asset_sha256"] == package["asset_sha256"]
    assert result.json()["pipeline_route"] == "VIDEO"
    package.pop("asset_sha256")
    assert client.get("/v1/content-jobs/offline-ceo-job/asset-preview").status_code == 409


def test_manifest_only_regeneration_retains_ceo_requirement(offline, monkeypatch):
    offline["job"]["status"] = "READY_FOR_REVIEW"
    package = offline["job"]["content_package"]
    package.pop("asset_forge_request")
    package["asset_forge_manifest"] = {"character": "CEO"}
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(content_jobs_api, "require_generation_execution", lambda: None)
    regenerated = content_jobs_api.regenerate_content_job("offline-ceo-job", BackgroundTasks(), "offline")
    assert regenerated["content_package"]["ceo_identity_required"] is True
    assert asset_provider.requires_ceo_asset_review(regenerated["content_package"])
    # Even with no surviving manifest/request, it must never become TEXT or generic art.
    body = []
    monkeypatch.setattr(content_router, "_supabase_request", lambda *a, **k: body.append(k["body"]) or [k["body"]])
    content_router._route_approved_row(regenerated)
    assert body[0]["status"] == "ASSET_QUEUED"
    assert body[0]["content_package"]["pipeline_route"] == "VISUAL"
    assert assets._process_claimed_asset(regenerated) is False
    assert offline["job"]["status"] == "ASSET_FAILED"
    assert offline["provider_calls"] == []


@pytest.mark.parametrize("failure", ["PENDING", "REJECTED", "stale_hash", "missing_hash", "changed_bytes", "video_url"])
def test_ceo_render_fails_closed_before_upload(offline, monkeypatch, failure):
    job = offline["job"]
    job.update(status="FINAL_RENDERING", audio_storage_path="j/audio.wav")
    digest = hashlib.sha256(MASTER.read_bytes()).hexdigest()
    package = job["content_package"]
    package.update(pipeline_route="VIDEO", asset_status="READY", asset_storage_path="j/image.png",
                   asset_sha256=digest, asset_review_sha256=digest, asset_review_status="APPROVED")
    if failure in {"PENDING", "REJECTED"}:
        package["asset_review_status"] = failure
    elif failure == "stale_hash":
        package["asset_review_sha256"] = "0" * 64
    elif failure == "missing_hash":
        package.pop("asset_sha256")
    elif failure == "video_url":
        job["video_url"] = "https://offline.invalid/unreviewed.mp4"
    monkeypatch.setattr(final_render, "_storage_download", lambda bucket, path, dest: dest.write_bytes(b"changed"))
    monkeypatch.setattr(final_render, "_duration", lambda _: 1.0)
    def forbidden(*a, **k):
        pytest.fail("Invalid CEO render reached FFmpeg, upload or external URL")
    monkeypatch.setattr(final_render.subprocess, "run", forbidden)
    monkeypatch.setattr(final_render, "_storage_upload", forbidden)
    monkeypatch.setattr(final_render, "_download_url", forbidden)
    monkeypatch.setattr(final_render, "_supabase_request", lambda *a, **k: job.update(k["body"]))
    assert final_render._process_claimed_render(deepcopy(job)) is False
    assert job["status"] == "RENDER_FAILED"


def test_real_offline_render_consumes_approved_ceo_and_binds_output(offline, monkeypatch):
    authorize_mock_only(monkeypatch)
    offline["job"]["content_package"]["pipeline_route"] = "VIDEO"
    assert assets.process_asset_job("offline-ceo-job")
    job = offline["job"]
    package = job["content_package"]
    package.update(asset_review_status="APPROVED", asset_review_sha256=package["asset_sha256"])
    job.update(status="FINAL_RENDERING", audio_storage_path="offline/audio.wav", script="CEO review proof")
    samples = BytesIO()
    with wave.open(samples, "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(b"".join(struct.pack("<h", int(2000 * math.sin(i * 2 * math.pi * 440 / 16000)))
                                 for i in range(16000)))
    downloads = []
    def download(bucket, path, dest):
        downloads.append((bucket, path))
        if bucket == final_render.AUDIO_BUCKET:
            dest.write_bytes(samples.getvalue())
        else:
            assert bucket == "content-assets" and path == package["asset_storage_path"]
            dest.write_bytes((offline["evidence_dir"] / "cover.png").read_bytes())
    uploads = []
    def upload(bucket, path, source, mime):
        assert bucket == "content-video" and mime == "video/mp4"
        data = source.read_bytes()
        assert path == f"{job['id']}/{hashlib.sha256(data).hexdigest()}.mp4"
        uploads.append(path)
        (offline["evidence_dir"] / "final.mp4").write_bytes(data)
    monkeypatch.setattr(final_render, "_storage_download", download)
    monkeypatch.setattr(final_render, "_storage_upload", upload)
    monkeypatch.setattr(final_render, "_supabase_request", lambda *a, **k: job.update(deepcopy(k["body"])))
    assert final_render._process_claimed_render(deepcopy(job)) is True, job.get("error_message")
    assert downloads == [("content-audio", "offline/audio.wav"), ("content-assets", package["asset_storage_path"])]
    assert job["status"] == "READY_TO_PUBLISH" and len(uploads) == 1
    asset_provider.require_ceo_render_provenance(job)
    assert job["render_qa"]["source_asset_sha256"] == package["asset_review_sha256"]
    (offline["evidence_dir"] / "render-job.json").write_text(json.dumps(job, indent=2))


@pytest.mark.parametrize("defect", ["missing", "source_hash", "source_path", "output_path", "video_url", "failed_qa"])
def test_unproven_ceo_video_blocked_at_all_publishing_boundaries(offline, monkeypatch, defect):
    job = offline["job"]
    package = job["content_package"]
    package.update(pipeline_route="VIDEO", asset_status="READY", asset_storage_path="j/ceo.png",
                   asset_sha256="a" * 64, asset_review_sha256="a" * 64, asset_review_status="APPROVED")
    job.update(status="READY_TO_PUBLISH", video_storage_path=f"{job['id']}/{'b' * 64}.mp4",
               render_qa={"status": "PASS", "source_asset_sha256": "a" * 64, "source_asset_storage_path": "j/ceo.png",
                          "output_sha256": "b" * 64, "output_storage_path": f"{job['id']}/{'b' * 64}.mp4"})
    asset_provider.require_ceo_render_provenance(job)
    if defect == "missing":
        job.pop("render_qa")
    elif defect == "source_hash":
        job["render_qa"]["source_asset_sha256"] = "c" * 64
    elif defect == "source_path":
        job["render_qa"]["source_asset_storage_path"] = "old/image.png"
    elif defect == "output_path":
        job["video_storage_path"] = "old/video.mp4"
    elif defect == "video_url":
        job["video_url"] = "https://offline.invalid/unproven.mp4"
    else:
        job["render_qa"]["status"] = "FAIL"
    monkeypatch.setattr(publishing_api, "require_publishing_enabled", lambda: None)
    monkeypatch.setattr(publishing_api, "_require_session", lambda _: None)
    monkeypatch.setattr(publishing_api, "_get_job", lambda _: deepcopy(job))
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    assert client.post("/v1/publishing/offline-ceo-job/publish-now", json={}).status_code == 400
    assert client.post("/v1/publishing/offline-ceo-job/schedule", json={"scheduled_time": "2099-01-01T00:00:00Z"}).status_code == 400
    for submit in (publishing_api._claim_submission, publora_publishing.submit_to_publora):
        with pytest.raises(ValueError):
            submit(job, platform_ids=[], scheduled_time=datetime.now(timezone.utc))


def test_unrelated_video_preserves_existing_source_and_output_contract(offline, monkeypatch):
    job = {"id": "ordinary", "status": "FINAL_RENDERING", "content_package": {},
           "video_url": "https://offline.invalid/ordinary.mp4", "audio_storage_path": "ordinary/audio.wav",
           "script": "Ordinary offline render"}
    calls = []
    monkeypatch.setattr(final_render, "_storage_download", lambda bucket, path, dest: dest.write_bytes(b"audio"))
    def download(url, dest):
        assert url == job["video_url"]
        calls.append("existing_video")
        dest.write_bytes(b"base")
    monkeypatch.setattr(final_render, "_download_url", download)
    monkeypatch.setattr(final_render, "_duration", lambda _: 1.0)
    def render(args, **kwargs):
        assert "-stream_loop" in args
        Path(args[-1]).write_bytes(b"ordinary-render")
    monkeypatch.setattr(final_render.subprocess, "run", render)
    monkeypatch.setattr(final_render, "_storage_upload", lambda bucket, path, source, mime: calls.append(path))
    monkeypatch.setattr(final_render, "_supabase_request", lambda *a, **k: job.update(k["body"]))
    assert final_render._process_claimed_render(deepcopy(job)) is True
    assert calls == ["existing_video", "ordinary/final.mp4"]
    assert job["status"] == "READY_TO_PUBLISH"
    assert "source_asset_sha256" not in job["render_qa"]


def test_verified_existing_ceo_render_can_be_released_by_matching_review(offline, monkeypatch):
    job = offline["job"]
    job.update(status="READY_FOR_REVIEW", render_status="READY",
               video_storage_path=f"{job['id']}/{'b' * 64}.mp4",
               render_qa={"status": "PASS", "source_asset_sha256": "a" * 64,
                          "source_asset_storage_path": "j/ceo.png", "output_sha256": "b" * 64,
                          "output_storage_path": f"{job['id']}/{'b' * 64}.mp4"})
    job["content_package"].update(pipeline_route="VIDEO", asset_status="READY", asset_sha256="a" * 64,
                                  asset_review_status="PENDING", asset_storage_path="j/ceo.png")
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    client = TestClient(forge.app, backend_options={"use_uvloop": True})
    response = client.post("/v1/content-jobs/offline-ceo-job/asset-review",
                           json={"decision": "APPROVED", "asset_sha256": "a" * 64})
    assert response.status_code == 200 and response.json()["status"] == "READY_TO_PUBLISH"
    asset_provider.require_ceo_render_provenance(response.json())
