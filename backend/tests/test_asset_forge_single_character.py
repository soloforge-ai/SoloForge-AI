import base64
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

import backend.asset_forge.main as main
from backend.output_quality import process_sheet

MASTER = Path(__file__).resolve().parents[2] / "frontend/assets/characters/ceo/references/master.png"


def payload(**overrides):
    return {"character": "CEO", "generation_layout": "single_character", "quantity": 1,
            "pose_intent": "presenting", "expression": "calm", **overrides}


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch):
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "false")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("Unauthorized network call"))


def test_single_quantity_only_and_required_intents():
    assert main.AssetForgeRequest(**payload()).quantity == 1
    for overrides in [{"generation_layout": "sticker_sheet"}, {"quantity": 4},
                      {"character": "Cat"}, {"pose_intent": None}, {"expression": None},
                      {"pose_intent": "presenting and pointing"}, {"expression": "laughing"},
                      {"messages": ["Presenting", "Pointing"]}, {"messages": ["Smile"]},
                      {"pose_intent": "thinking", "expression": "subtle_smile"}]:
        with pytest.raises(ValidationError): main.AssetForgeRequest(**payload(**overrides))
    assert main.AssetForgeRequest(quantity=4).generation_layout == "sticker_sheet"
    assert main.AssetForgeRequest(quantity=24).quantity == 24


@pytest.mark.parametrize("wardrobe", list(main.CEO_OUTFITS))
def test_single_prompt_identity_and_wardrobes(wardrobe):
    req = main.AssetForgeRequest(**payload(wardrobe_variant=wardrobe))
    prompt = main._build_prompt(req, 1, 1, True)
    assert "exactly one CEO character" in prompt
    assert "Exactly one pose and exactly one expression" in prompt
    assert main.CEO_OUTFITS[wardrobe] in prompt
    assert "NEVER show teeth" in prompt and "No wings, halo" in prompt
    assert "large black glasses" in prompt and "Full figure" in prompt
    for sheet_instruction in ["columns x", "2x2", "STICKER MESSAGE", "separate sticker poses", "every cell"]:
        assert sheet_instruction not in prompt


def test_campaign_and_missing_reference():
    req = main.AssetForgeRequest(**payload(wardrobe_variant="creator", campaign_id="manifest_glow_lab"))
    prompt = main._build_prompt(req, 1, 1, True)
    assert "MANIFEST GLOW LAB" in prompt
    assert main.CEO_OUTFITS["default"] in prompt
    assert main.CEO_OUTFITS["creator"] not in prompt
    with pytest.raises(ValueError): main._build_prompt(req, 1, 1, False)


def test_actual_runtime_memory_and_full_image_routing():
    import runtime
    request = runtime.asset_forge_main.AssetForgeRequest(**payload())
    prompt = runtime.asset_forge_main._build_prompt(request, 1, 1, True)
    assert "APPROVED CHARACTER DNA" in prompt
    assert "exactly one CEO character" in prompt
    image = io.BytesIO(); Image.new("RGB", (70, 39), "white").save(image, "PNG")
    files, original = runtime.asset_forge_main._process_sheet(image.getvalue(), request)
    assert len(files) == 1 and original == image.getvalue()
    assert Image.open(io.BytesIO(files[0][1])).size == (70, 39)


def test_single_processing_preserves_edges_dimensions_and_pixels():
    im = Image.new("RGB", (81, 47), "white")
    im.putpixel((0, 0), (255, 0, 0))
    im.putpixel((80, 46), (0, 0, 255))
    b = io.BytesIO(); im.save(b, "PNG")
    source = b.getvalue()
    for processor in [main._process_sheet, process_sheet]:
        files, original = processor(source, main.AssetForgeRequest(**payload()))
        assert original == source and len(files) == 1
        out = Image.open(io.BytesIO(files[0][1]))
        assert out.size == (81, 47)
        assert out.getpixel((0, 0)) == (255, 0, 0, 255)
        assert out.getpixel((80, 46)) == (0, 0, 255, 255)
        assert out.getpixel((40, 20)) == (255, 255, 255, 255)


def setup_client(monkeypatch):
    # Mock processing contract only; production remains execution-locked.
    monkeypatch.setattr(main, "require_generation_execution", lambda: None)
    monkeypatch.setattr(main, "get_pollinations_access_token_from_authorization", lambda _: "test-only-token")
    monkeypatch.setattr(main, "_load_character_reference", lambda _: MASTER.read_bytes())
    monkeypatch.setattr(main, "_generate_local_fallback_sheet", lambda *a: pytest.fail("Single must not fallback"))
    monkeypatch.setattr(main, "stamp_image_bytes", lambda *a: pytest.fail("Single must not add logos"))
    return TestClient(main.app)


def test_api_one_mock_adapter_call_and_manifest(monkeypatch):
    client = setup_client(monkeypatch)
    b = io.BytesIO(); Image.new("RGB", (80, 55), "red").save(b, "PNG")
    source = b.getvalue()
    calls = []
    def fake_adapter(prompt, reference, token):
        calls.append(prompt)
        assert hashlib.sha256(reference).hexdigest() == main.CEO_MASTER_SHA256
        return source
    monkeypatch.setattr(main, "_generate_sheet", fake_adapter)
    response = client.post("/v1/asset-forge/generate", json=payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(calls) == 1 and len(body["files"]) == 1
    assert body["generation_layout"] == "single_character"
    assert body["generation_mode"] == "pollinations" # Mock contract only, not real visual evidence.
    assert base64.b64decode(body["source_image_base64"]) == source
    manifest = body["output_manifest"]
    assert manifest["reference_sha256"] == main.CEO_MASTER_SHA256
    assert manifest["quantity"] == 1 and manifest["pose_intent"] == "presenting"
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(body["zip_base64"]))) as archive:
        names = archive.namelist()
        assert not any("sticker" in n or "sheet" in n for n in names)
        assert any(n.endswith("original_image.png") for n in names)
        raw_path = next(n for n in names if n.endswith("raw/provider_image.bin"))
        assert archive.read(raw_path) == source
        assert hashlib.sha256(archive.read(raw_path)).hexdigest() == manifest["source_sha256"]
        assert json.loads(archive.read(next(n for n in names if n.endswith("manifest.json")))) == manifest


def test_provider_timeout_no_fallback_no_retry(monkeypatch):
    client = setup_client(monkeypatch)
    calls = []
    def fail(*a):
        calls.append(1)
        raise HTTPException(status_code=504, detail="provider detail must not be exposed")
    monkeypatch.setattr(main, "_generate_sheet", fail)
    response = client.post("/v1/asset-forge/generate", json=payload())
    assert response.status_code == 504 and len(calls) == 1
    assert "Do not automatically retry" in response.text
    assert "provider detail" not in response.text


def test_missing_session_and_bad_master_fail_before_adapter(monkeypatch):
    client = setup_client(monkeypatch)
    monkeypatch.setattr(main, "_generate_sheet", lambda *a: pytest.fail("Provider must not be called"))
    monkeypatch.setattr(main, "_load_character_reference", lambda _: b"bad master")
    assert client.post("/v1/asset-forge/generate", json=payload()).status_code == 409
    monkeypatch.setattr(main, "get_pollinations_access_token_from_authorization", lambda _: None)
    assert client.post("/v1/asset-forge/generate", json=payload()).status_code == 401
