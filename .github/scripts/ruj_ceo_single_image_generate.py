"""Manually gated CEO character-image generation: maximum two API calls."""
import hashlib
import io
import json
import os
from pathlib import Path

from PIL import Image
from backend.asset_forge import runtime

ROOT = Path("visual-qa-artifacts")


def main():
    proof = json.loads((ROOT / "character-image-preflight.json").read_text())
    assert proof["mode"] == "SINGLE_CHARACTER_OFFLINE"
    assert proof["pollinations_called"] is False
    assert len(proof["cases"]) == 2
    master = Path("frontend/assets/characters/ceo/references/master.png").read_bytes()
    expected = json.loads((ROOT / "visual-qa-preflight.json").read_text())["master_sha256"]
    assert hashlib.sha256(master).hexdigest() == expected
    prompts = []
    for case in proof["cases"]:
        prompt = (ROOT / f'{case["case"]}-character-image-prompt.txt').read_text()
        assert hashlib.sha256(prompt.encode()).hexdigest() == case["prompt_sha256"]
        assert "SINGLE CHARACTER IMAGE MODE" in prompt
        prompts.append((case["case"], prompt))
    token = os.environ.get("POLLINATIONS_QA_TOKEN", "")
    if not token:
        raise RuntimeError("BLOCKED: missing Pollinations QA token")
    report = {"mode":"SINGLE_CHARACTER_POLLINATIONS","visual_qa_status":"REVIEW_REQUIRED",
              "max_image_requests":2,"master_sha256":expected,"cases":[]}
    try:
        for name,prompt in prompts:
            record = {"case":name,"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),"status":"STARTED"}
            report["cases"].append(record)
            try:
                data = runtime.asset_forge_main._generate_sheet(prompt,master,token)
                output = io.BytesIO()
                with Image.open(io.BytesIO(data)) as img:
                    img.convert("RGB").save(output,format="PNG")
                data = output.getvalue()
                (ROOT / f"{name}-character-image-generated.png").write_bytes(data)
                record["image_sha256"] = hashlib.sha256(data).hexdigest()
                record["status"] = "GENERATED_REVIEW_REQUIRED"
            except Exception:
                record["status"] = "GENERATION_FAILED"
                report["visual_qa_status"] = "BLOCKED"
                raise
    finally:
        (ROOT / "character-image-report.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
