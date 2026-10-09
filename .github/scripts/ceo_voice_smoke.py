"""Manually gated CEO Pilot #001 one-sentence Thai TTS smoke test.

One POST only. No retry, no fallback, no video/image generation.
"""
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

TEXT = "งานเยอะจนไม่รู้จะเริ่มตรงไหน?"
MODEL = "tts-1"
VOICE = "onyx"
URL = "https://gen.pollinations.ai/v1/audio/speech"


def main():
    root = Path("voice-smoke-evidence")
    root.mkdir(exist_ok=True)
    expected = os.getenv("CEO_VOICE_SMOKE_MODE", "prepare")
    if expected not in {"prepare", "generate"}:
        raise RuntimeError("Mode must be prepare or generate")
    report = {"test": "CEO_Pilot_001_Shot_01", "mode": expected,
              "script": TEXT, "model": MODEL, "voice": VOICE,
              "api_calls": 0, "status": "PREPARED"}
    try:
        if expected == "generate":
            token = os.environ.get("POLLINATIONS_QA_TOKEN")
            if not token:
                raise RuntimeError("BLOCKED: POLLINATIONS_QA_TOKEN missing")
            request = urllib.request.Request(
                URL,
                data=json.dumps({"model": MODEL, "voice": VOICE, "input": TEXT,
                                 "response_format": "mp3"}, ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                         "Accept": "audio/mpeg"},
                method="POST",
            )
            report["api_calls"] = 1
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    content_type = response.headers.get("Content-Type", "")
                    audio = response.read(12_000_000)
            except urllib.error.HTTPError as exc:
                report["http_status"] = exc.code
                raise RuntimeError("Pollinations TTS HTTP error " + str(exc.code)) from None
            if "audio" not in content_type.lower() and not audio.startswith(b"ID3") and not audio.startswith(b"\\xff\\xfb"):
                raise RuntimeError("Pollinations did not return recognized audio")
            if len(audio) < 2000:
                raise RuntimeError("Unexpectedly small audio")
            path = root / "ceo_pilot_001_shot01_th.mp3"
            path.write_bytes(audio)
            report["audio_sha256"] = hashlib.sha256(audio).hexdigest()
            report["audio_bytes"] = len(audio)
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, check=True,
            )
            duration = float(result.stdout.strip())
            report["duration_seconds"] = round(duration, 3)
            report["target_slot_seconds"] = 4
            report["duration_fits_slot"] = duration <= 4
            report["status"] = "AUDIO_GENERATED_REVIEW_REQUIRED"
    except Exception:
        report["status"] = "BLOCKED"
        raise
    finally:
        (root / "voice-smoke-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
