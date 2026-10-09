"""CEO single-character image prompt QA. No API calls."""
import hashlib
import json
from pathlib import Path

ROOT = Path("visual-qa-artifacts")
CASES = ("creator", "fitness")


def make_prompt(compact):
    marker = "\nSTICKER MESSAGE INTENT:"
    memory_marker = "\n\nAPPROVED CHARACTER DNA — MEMORY FOUNDATION"
    assert compact.count(marker) == 1
    assert compact.count(memory_marker) == 1
    before, rest = compact.split(marker, 1)
    _, memory = rest.split(memory_marker, 1)
    original = "Create a commercial-quality sticker sheet for the character CEO."
    assert before.count(original) == 1
    before = before.replace(original, "Create one commercial-quality image of exactly ONE CEO character.", 1)
    composition = """
SINGLE CHARACTER IMAGE MODE:
- Exactly one CEO per image: no sticker sheet, grid, collage, montage, or duplicated figures.
- One continuous full-body pose from hair to soles of both shoes. Both feet visible, no cropping.
- Centered with generous margin in a simple clean studio background. No captions or text.
- Preserve master face, hair, black glasses and chibi proportions.
- Use the approved wardrobe variant even when the master is wearing the default white suit.
- Smile very slightly with closed mouth; no visible teeth; soft pink blush when happy or shy.
"""
    result = (before + composition + memory_marker + memory).strip()
    assert "Create exactly 4 separate sticker poses" not in result
    assert "STICKER MESSAGE INTENT" not in result
    assert "CEO FACIAL EXPRESSION — SHORT A/B VARIANT" in result
    return result


def main():
    proof = json.loads((ROOT / "expression-ab-preflight.json").read_text())
    assert proof["pollinations_called"] is False
    out = []
    for case in CASES:
        source = (ROOT / f"{case}-compact-b-prompt.txt").read_text()
        record = next(x for x in proof["cases"] if x["case"] == case)
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        assert source_hash == record["compact_b_sha256"]
        prompt = make_prompt(source)
        outfit = "Black creator hoodie" if case == "creator" else "Appropriate sportswear"
        assert outfit in prompt
        (ROOT / f"{case}-character-image-prompt.txt").write_text(prompt)
        out.append({"case": case, "source_sha256": source_hash,
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    (ROOT / "character-image-preflight.json").write_text(json.dumps({
        "mode": "SINGLE_CHARACTER_OFFLINE", "pollinations_called": False,
        "generated_images": 0, "cases": out
    }, indent=2) + "\n")
    print("PASS: 2 verified single-character prompts; no API calls")


if __name__ == "__main__":
    main()
