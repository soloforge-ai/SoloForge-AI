from pathlib import Path

from .config import (
    PROJECT_ROOT,
    SCAN_FOLDERS,
    IGNORE_FOLDERS,
    SUPPORTED_EXTENSIONS,
)


class ProjectScanner:
    def scan(self) -> list[Path]:
        files: list[Path] = []

        for folder in SCAN_FOLDERS:
            root = PROJECT_ROOT / folder

            if not root.exists():
                continue

            for file in root.rglob("*"):

                if not file.is_file():
                    continue

                if file.suffix not in SUPPORTED_EXTENSIONS:
                    continue

                if any(part in IGNORE_FOLDERS for part in file.parts):
                    continue

                files.append(file)

        return sorted(files)