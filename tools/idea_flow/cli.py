from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import DEFAULT_DB_PATH
from .service import IdeaFlowService


def print_rows(rows: list[dict[str, object]]) -> None:
    if not rows:
        print("No ideas found.")
        return
    for row in rows:
        print(f"#{row['id']} [{row['status']}] {row['title']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SoloForge Idea Flow")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("capture")
    p.add_argument("text", nargs="+")

    p = sub.add_parser("list")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=30)

    p = sub.add_parser("search")
    p.add_argument("query", nargs="+")

    p = sub.add_parser("view")
    p.add_argument("id", type=int)

    p = sub.add_parser("history")
    p.add_argument("id", type=int)

    p = sub.add_parser("research")
    p.add_argument("id", type=int)
    p.add_argument("text", nargs="+")

    p = sub.add_parser("score")
    p.add_argument("id", type=int)
    p.add_argument("demand", type=int)
    p.add_argument("feasibility", type=int)
    p.add_argument("strategic_fit", type=int)
    p.add_argument("--notes", default="")

    for command, target in (
        ("triage", "TRIAGED"),
        ("graduate", "GRADUATED"),
        ("park", "PARKED"),
        ("reject", "REJECTED"),
        ("experiment", "EXPERIMENT"),
        ("validate", "VALIDATED"),
        ("kill", "KILLED"),
    ):
        p = sub.add_parser(command)
        p.set_defaults(target_status=target)
        p.add_argument("id", type=int)
        p.add_argument("--reason", default="")

    p = sub.add_parser("note")
    p.add_argument("id", type=int)
    p.add_argument("text", nargs="+")
    p.add_argument("--type", default="NOTE")
    p.add_argument("--source-url")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    with IdeaFlowService(Path(args.db)) as service:
        if args.command == "capture":
            idea_id = service.capture(" ".join(args.text), source="cli", actor="cli")
            print(f"Captured Idea #{idea_id}")
        elif args.command == "list":
            print_rows(service.list(status=args.status, limit=args.limit))
        elif args.command == "search":
            print_rows(service.search(" ".join(args.query)))
        elif args.command == "view":
            print(json.dumps(service.get(args.id), ensure_ascii=False, indent=2))
        elif args.command == "history":
            print(json.dumps(service.history(args.id), ensure_ascii=False, indent=2))
        elif args.command == "research":
            service.mark_researched(args.id, " ".join(args.text), actor="cli")
            print(f"Idea #{args.id} -> RESEARCHED")
        elif args.command == "score":
            result = service.evaluate(
                args.id,
                demand=args.demand,
                feasibility=args.feasibility,
                strategic_fit=args.strategic_fit,
                notes=args.notes,
                evaluator="cli",
            )
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == "note":
            note_id = service.add_note(
                args.id,
                " ".join(args.text),
                note_type=args.type,
                source_url=args.source_url,
                actor="cli",
            )
            print(f"Added note #{note_id}")
        elif hasattr(args, "target_status"):
            service.transition(args.id, args.target_status, actor="cli", reason=args.reason)
            print(f"Idea #{args.id} -> {args.target_status}")


if __name__ == "__main__":
    main()
