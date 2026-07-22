from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCAN_FOLDERS = [
    "frontend/lib",
    "backend",
    "feed_processor",
    "docs",
    "tools",
    "rules",
    "prompts",
]

IGNORE_FOLDERS = {
    ".git",
    ".dart_tool",
    "build",
    "__pycache__",
    ".idea",
    ".vscode",
    "ios",
    "android",
    "linux",
    "macos",
    "windows",
    "web",
}

SUPPORTED_EXTENSIONS = {
    ".dart",
    ".py",
    ".json",
    ".md",
}