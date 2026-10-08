"""Manually gated image QA runner. Exactly four image edit calls at most."""
import hashlib
import json
import os
from pathlib import Path

from main import AssetForgeRequest, _grid
# Import runtime to activate the same prompt/character-reference patches as production.
from backend.asset_forge import runtime as asset_runtime


def main():
    root = Path("visual-qa-artifacts")
    root.mkdir(exist_ok=True)
    master = Path("frontend/assets/characters/ceo/references/master.png")
    if not master.is_file():
        raise RuntimeError("BLOCKED: approved CEO master missing")
    token = os.environ.get("POLLINATIONS_QA_TOKEN", "")
    if not token:
        raise RuntimeError("BLOCKED: POLLINATIONS_QA_TOKEN secret not configured")
    master_bytes = master.read_bytes()
    if len(master_bytes) < 1000:
        raise RuntimeError("BLOCKED: CEO master image file too small")
    cases = [
        ("canon", "default", None),
        ("creator", "creator", None),
        ("fitness", "fitness", None),
        ("manifest_glow_lab", "creator", "manifest_glow_lab"),
    ]
    report = {
        "mode": "REAL_POLLINATIONS", "visual_qa_status": "REVIEW_REQUIRED",
        "master_sha256": hashlib.sha256(master_bytes).hexdigest(),
        "max_image_requests": len(cases), "cases": [],
    }
    try:
        for name, wardrobe, campaign in cases:
            request = AssetForgeRequest(
                character="CEO", product="Visual QA",
                theme="CEO identity consistency visual QA",
                style="Premium 3D Chibi", quantity=4,
                messages=["Presenting", "Pointing", "Thinking", "Smiling"],
                wardrobe_variant=wardrobe, campaign_id=campaign,
            )
            prompt = asset_runtime.asset_forge_main._build_prompt(request, *_grid(4), True)
            record = {"case": name, "wardrobe_variant": wardrobe, "campaign_id": campaign,
                      "status": "STARTED"}
            report["cases"].append(record)
            (root / f"{name}-prompt.txt").write_text(prompt, encoding="utf-8")
            (root / f"{name}-request.json").write_text(request.model_dump_json(indent=2), encoding="utf-8")
            # Direct generation: no app endpoint and absolutely NO local fallback.
            try:
                result = asset_runtime.asset_forge_main._generate_sheet(prompt, master_bytes, token)
            except Exception:
                record["status"] = "GENERATION_FAILED"
                report["visual_qa_status"] = "BLOCKED"
                raise
            from PIL import Image
            import io
            with Image.open(io.BytesIO(result)) as image:
                image.verify()
            (root / f"{name}-generated.png").write_bytes(_normalize_png(result))
            record["status"] = "GENERATED_REVIEW_REQUIRED"
    finally:
        (root / "visual-qa-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _normalize_png(data):
    import io
    from PIL import Image
    out = io.BytesIO()
    with Image.open(io.BytesIO(data)) as img:
        img.convert("RGB").save(out, "PNG")
    return out.getvalue()


if __name__ == "__main__":
    main()
