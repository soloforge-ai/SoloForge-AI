"""Offline A/B prompt evidence: original PR-155 baseline vs shortened expression lock.

No Pollinations calls and no changes to the production or generation prompt.
The expected baseline SHA256 values come from the first CEO Visual QA evidence ZIP.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("visual-qa-artifacts")
BASELINE_SHA256 = {
    "canon": "d8d738c58e94d57b32bbd1fe056aba46d25baec7a4188533b6840a6d10c8cbd1",
    "creator": "ecacc03f3b5a220b05e7611d6bc1811a7e86ccfa21bd55881d30c9f339f45278",
    "fitness": "1027ac1dc83de250993c3154c3af939158479bf71239f1b202f56fd27b674258",
    "manifest_glow_lab": "a3319117efe8ee0be5d5e7d0313dcf104afb97cef5b98991a8e36b5fe6ed71e0",
}
FULL_EXPRESSION = re.compile(
    r"\n\n\nNON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK:\n(?:-[^\n]*\n)+"
)
SHORT_EXPRESSION = (
    "\n\n\nCEO FACIAL EXPRESSION — SHORT A/B VARIANT:\n"
    "- Keep a calm, composed, mostly neutral expression. Smile only slightly with mouth closed; no visible teeth.\n"
    "- When pleased, happy, or shy, use a tiny closed-mouth smile and subtle natural pink blush on both cheeks.\n"
    "- Keep the same approved face, glasses, hairstyle, and proportions.\n"
)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_variants(prompt: str) -> tuple[str, str]:
    matches = list(FULL_EXPRESSION.finditer(prompt))
    assert len(matches) == 1, "Expected exactly one full CEO expression lock"
    match = matches[0]
    # The old PR-155 prompt had one newline here; the full lock added three.
    baseline = prompt[: match.start()] + "\n" + prompt[match.end() :]
    compact = prompt[: match.start()] + SHORT_EXPRESSION + prompt[match.end() :]
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" not in compact
    assert "APPROVED CHARACTER DNA" in baseline
    assert "Create exactly 4 separate sticker poses in a clean 2 columns x 2 rows grid." in baseline
    assert "Create exactly 4 separate sticker poses in a clean 2 columns x 2 rows grid." in compact
    return baseline, compact


def main() -> None:
    rows = []
    for case, expected_sha in BASELINE_SHA256.items():
        prompt = (ROOT / f"{case}-prompt.txt").read_text(encoding="utf-8")
        baseline, compact = build_variants(prompt)
        assert sha256(baseline) == expected_sha, f"{case}: baseline diverged from first-run evidence"
        for phrase in ("APPROVED CONTEXTUAL WARDROBE OVERRIDE", "MANIFEST GLOW LAB: Keep the canonical"):
            assert (phrase in baseline) == (phrase in compact), f"{case}: wardrobe changed"
        assert "no visible teeth" in compact and "pink blush on both cheeks" in compact
        assert "NEVER show teeth" in prompt
        (ROOT / f"{case}-baseline-a-prompt.txt").write_text(baseline, encoding="utf-8")
        (ROOT / f"{case}-compact-b-prompt.txt").write_text(compact, encoding="utf-8")
        rows.append({
            "case": case, "baseline_a_sha256": sha256(baseline),
            "compact_b_sha256": sha256(compact),
            "baseline_matches_first_run": True,
            "other_prompt_sections_unchanged": True,
        })
    (ROOT / "expression-ab-preflight.json").write_text(
        json.dumps({"mode": "OFFLINE_AB_ONLY", "pollinations_called": False,
                    "generated_images": 0, "baseline": "first CEO visual QA",
                    "variant_b": "shortened facial expression only",
                    "cases": rows}, indent=2) + "\n", encoding="utf-8",
    )
    print("PASS: four exact first-run baselines and four compact expression variants; zero API calls")


if __name__ == "__main__":
    main()
