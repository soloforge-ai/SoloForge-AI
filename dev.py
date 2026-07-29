#!/usr/bin/env python3
"""
SoloForge AI Developer Launcher
Sprint 32A
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(title: str, command: list[str], cwd=None):

    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

    result = subprocess.run(
        command,
        cwd=cwd or ROOT,
    )

    if result.returncode != 0:
        print("\n❌ Command Failed")
        input("\nPress Enter to continue...")
        return False

    print("\n✅ Done")
    input("\nPress Enter to continue...")
    return True


def flutter():
    return run(
        "Flutter",
        ["flutter", "run"],
        ROOT / "frontend",
    )


def pipeline():

    if not run(
        "Product Pipeline",
        ["python", "run.py"],
        ROOT / "feed_processor",
    ):
        return

    run(
        "Sync Flutter",
        ["python", "sync_flutter.py"],
        ROOT / "feed_processor",
    )


def miniboss_test():
    run(
        "MiniBoss Test",
        ["python", "test_miniboss.py"],
        ROOT / "feed_processor",
    )


def scanner():
    run(
        "Project Scanner",
        ["python", "main.py"],
        ROOT / "tools" / "scanner",
    )


def full_build():

    if not run(
        "MiniBoss Test",
        ["python", "test_miniboss.py"],
        ROOT / "feed_processor",
    ):
        return

    if not run(
        "Product Pipeline",
        ["python", "run.py"],
        ROOT / "feed_processor",
    ):
        return

    if not run(
        "Sync Flutter",
        ["python", "sync_flutter.py"],
        ROOT / "feed_processor",
    ):
        return

    if not run(
        "Project Scanner",
        ["python", "main.py"],
        ROOT / "tools" / "scanner",
    ):
        return

    run(
        "Flutter",
        ["flutter", "run"],
        ROOT / "frontend",
    )


def menu():

    while True:

        print("\n")
        print("=" * 60)
        print("🚀 SoloForge AI Developer Launcher")
        print("=" * 60)
        print("[1] 🎨 Run Flutter")
        print("[2] 📦 Product Pipeline")
        print("[3] 🧠 MiniBoss Test")
        print("[4] 🔍 Project Scanner")
        print("[5] 🚀 Full Build")
        print("[0] Exit")
        print("=" * 60)

        choice = input("Select : ").strip()

        if choice == "1":
            flutter()

        elif choice == "2":
            pipeline()

        elif choice == "3":
            miniboss_test()

        elif choice == "4":
            scanner()

        elif choice == "5":
            full_build()

        elif choice == "0":
            print("\n👋 Bye")
            sys.exit()

        else:
            print("\nInvalid selection")


if __name__ == "__main__":
    menu()