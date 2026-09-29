from pathlib import Path

from tools.scanner.config import PROJECT_ROOT
from tools.scanner.scanner import ProjectScanner


def test_generated_scanner_output_is_not_scanned() -> None:
    output_dir = PROJECT_ROOT / "tools" / "scanner" / "output"
    probe = output_dir / "_scanner_output_probe.md"
    probe.write_text("# generated probe\n", encoding="utf-8")
    try:
        scanned = {path.resolve() for path in ProjectScanner().scan()}
        assert probe.resolve() not in scanned
    finally:
        probe.unlink(missing_ok=True)
