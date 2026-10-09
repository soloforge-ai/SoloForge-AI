"""Assemble pinned PR-155 wardrobe QA with the approved CEO expression lock, offline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SOURCE = Path("expression-source/backend/asset_forge/main.py")
TARGET = Path("backend/asset_forge/main.py")
START = '    ceo_expression_lock = """'
END = '    return f"""\nCreate a commercial-quality sticker sheet'
INSERT_AFTER = "{no_wings_rule}\n"


def install_expression_lock() -> None:
    approved = SOURCE.read_text(encoding="utf-8")
    target = TARGET.read_text(encoding="utf-8")
    assert approved.count(START) == 1, "approved lock missing or duplicated"
    assert target.count(END) == 1, "PR-155 prompt contract changed"
    assert target.count(INSERT_AFTER) == 1, "PR-155 insertion point changed"
    assert "wardrobe_variant" in target, "PR-155 wardrobe support missing"
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" not in target, "lock already present"
    lock = approved[approved.index(START):approved.index(END)]
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" in lock
    assert '""" if request.character.strip().lower() == "ceo" else ""' in lock
    target = target.replace(END, lock + END, 1)
    target = target.replace(INSERT_AFTER, INSERT_AFTER + "{ceo_expression_lock}\n", 1)
    TARGET.write_text(target, encoding="utf-8")


def verify_prompts() -> None:
    from main import AssetForgeRequest, _grid
    from backend.asset_forge import runtime

    root = Path("visual-qa-artifacts")
    root.mkdir(exist_ok=True)
    master = Path("frontend/assets/characters/ceo/references/master.png")
    if not master.is_file():
        raise RuntimeError("BLOCKED: CEO master not found")
    cases = [
        ("canon", "default", None),
        ("creator", "creator", None),
        ("fitness", "fitness", None),
        ("manifest_glow_lab", "creator", "manifest_glow_lab"),
    ]
    results = []
    for name, wardrobe, campaign in cases:
        request = AssetForgeRequest(
            character="CEO", product="Visual QA",
            theme="CEO identity consistency visual QA",
            style="Premium 3D Chibi", quantity=4,
            messages=["Presenting", "Pointing", "Thinking", "Smiling"],
            wardrobe_variant=wardrobe, campaign_id=campaign,
        )
        prompt = runtime.asset_forge_main._build_prompt(request, *_grid(4), True)
        assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" in prompt, name
        assert "NEVER show teeth" in prompt, name
        assert "soft natural pink blush on both cheeks" in prompt, name
        assert "NO wings" in prompt, name
        if name in ("creator", "fitness"):
            assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" in prompt, name
        elif name == "manifest_glow_lab":
            assert "MANIFEST GLOW LAB: Keep the canonical" in prompt, name
            assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt, name
        else:
            assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt, name
        (root / (name + "-prompt.txt")).write_text(prompt, encoding="utf-8")
        (root / (name + "-request.json")).write_text(request.model_dump_json(indent=2), encoding="utf-8")
        results.append({"case": name, "status": "PROMPT_VERIFIED",
                        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    (root / "visual-qa-preflight.json").write_text(
        json.dumps({"mode": "PREPARE_ONLY", "pollinations_called": False,
                    "visual_qa_status": "NOT_RUN",
                    "master_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
                    "cases": results}, indent=2) + "\n", encoding="utf-8",
    )
    print("PASS: four composed prompts verified offline; no API calls")


if __name__ == "__main__":
    install_expression_lock()
    verify_prompts()
