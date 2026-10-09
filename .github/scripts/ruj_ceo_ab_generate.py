"""Manual two-case Pollinations A/B visual test; calls API at most twice per run.

Requires the offline preflight and A/B SHA verification before use.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from backend.asset_forge import runtime as asset_runtime

ROOT = Path("visual-qa-artifacts")
ALLOWED = {"baseline_a", "compact_b"}
CASES = ("creator", "fitness")


def main() -> None:
    selected = os.environ.get("CEO_AB_VARIANT", "")
    if selected not in ALLOWED:
        raise RuntimeError("BLOCKED: select baseline_a or compact_b")
    proof_file = ROOT / "expression-ab-preflight.json"
    if not proof_file.is_file():
        raise RuntimeError("BLOCKED: offline A/B verification evidence missing")
    proof = json.loads(proof_file.read_text(encoding="utf-8"))
    if proof.get("pollinations_called") is not False or len(proof.get("cases", [])) != 4:
        raise RuntimeError("BLOCKED: invalid A/B preflight")
    master = Path("frontend/assets/characters/ceo/references/master.png")
    master_bytes = master.read_bytes()
    if hashlib.sha256(master_bytes).hexdigest() != json.loads(
        (ROOT / "visual-qa-preflight.json").read_text(encoding="utf-8")
    )["master_sha256"]:
        raise RuntimeError("BLOCKED: master reference changed")
    prompts = []
    suffix = "baseline-a" if selected == "baseline_a" else "compact-b"
    for name in CASES:
        source = ROOT / f"{name}-{suffix}-prompt.txt"
        prompt = source.read_text(encoding="utf-8")
        record = next((x for x in proof["cases"] if x["case"] == name), None)
        if not record or hashlib.sha256(prompt.encode("utf-8")).hexdigest() != record[f"{selected}_sha256"]:
            raise RuntimeError(f"BLOCKED: {name} prompt SHA256 mismatch")
        if "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt:
            raise RuntimeError(f"BLOCKED: {name} wardrobe override absent")
        prompts.append((name, prompt))
    token = os.environ.get("POLLINATIONS_QA_TOKEN", "")
    if not token:
        raise RuntimeError("BLOCKED: POLLINATIONS_QA_TOKEN not set")

    report = {
        "mode": "CONTROLLED_AB_POLLINATIONS", "variant": selected,
        "max_image_requests": len(CASES), "visual_qa_status": "REVIEW_REQUIRED",
        "master_sha256": hashlib.sha256(master_bytes).hexdigest(), "cases": [],
    }
    try:
        for name, prompt in prompts:
            row = {"case": name, "variant": selected,
                   "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                   "status": "STARTED"}
            report["cases"].append(row)
            try:
                image_bytes = asset_runtime.asset_forge_main._generate_sheet(prompt, master_bytes, token)
                from PIL import Image
                import io
                output = io.BytesIO()
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image.convert("RGB").save(output, "PNG")
                normalized = output.getvalue()
                (ROOT / f"{name}-{selected}-generated.png").write_bytes(normalized)
                row["image_sha256"] = hashlib.sha256(normalized).hexdigest()
                row["status"] = "GENERATED_REVIEW_REQUIRED"
            except Exception:
                row["status"] = "GENERATION_FAILED"
                report["visual_qa_status"] = "BLOCKED"
                raise
    finally:
        (ROOT / "visual-qa-ab-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
