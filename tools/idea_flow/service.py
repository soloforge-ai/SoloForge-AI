from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import scoring
from .db import DEFAULT_DB_PATH, connect, migrate
from .state_machine import validate_transition


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class IdeaFlowService:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.con = connect(self.db_path)
        migrate(self.con)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "IdeaFlowService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _get(self, idea_id: int) -> sqlite3.Row:
        row = self.con.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        if row is None:
            raise KeyError(f"Idea #{idea_id} not found")
        return row

    def capture(self, body: str, *, source: str = "manual", actor: str | None = None) -> int:
        body = body.strip()
        if not body:
            raise ValueError("Idea body cannot be empty")
        title = body.splitlines()[0].strip()[:120]
        now = utc_now()
        actor = actor or source
        with self.con:
            cur = self.con.execute(
                """
                INSERT INTO ideas(title, body, source, status, created_at, updated_at)
                VALUES (?, ?, ?, 'CAPTURED', ?, ?)
                """,
                (title, body, source, now, now),
            )
            idea_id = int(cur.lastrowid)
            self.con.execute(
                """
                INSERT INTO idea_events(
                    idea_id,event_type,from_status,to_status,actor,reason,metadata_json,created_at
                ) VALUES (?, 'CAPTURED', NULL, 'CAPTURED', ?, 'idea captured', NULL, ?)
                """,
                (idea_id, actor, now),
            )
        return idea_id

    def transition(self, idea_id: int, to_status: str, *, actor: str = "manual", reason: str = "") -> None:
        current = self._get(idea_id)
        from_status = current["status"]
        validate_transition(from_status, to_status)
        now = utc_now()
        with self.con:
            self.con.execute(
                "UPDATE ideas SET status = ?, updated_at = ? WHERE id = ?",
                (to_status, now, idea_id),
            )
            self.con.execute(
                """
                INSERT INTO idea_events(
                    idea_id,event_type,from_status,to_status,actor,reason,metadata_json,created_at
                ) VALUES (?, 'STATUS_CHANGED', ?, ?, ?, ?, NULL, ?)
                """,
                (idea_id, from_status, to_status, actor, reason or None, now),
            )

    def add_note(
        self,
        idea_id: int,
        body: str,
        *,
        note_type: str = "NOTE",
        source_url: str | None = None,
        actor: str = "manual",
    ) -> int:
        self._get(idea_id)
        body = body.strip()
        if not body:
            raise ValueError("Note cannot be empty")
        note_type = note_type.upper()
        now = utc_now()
        with self.con:
            cur = self.con.execute(
                """
                INSERT INTO idea_notes(idea_id,note_type,body,source_url,created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (idea_id, note_type, body, source_url, now),
            )
            note_id = int(cur.lastrowid)
            self.con.execute(
                """
                INSERT INTO idea_events(
                    idea_id,event_type,from_status,to_status,actor,reason,metadata_json,created_at
                ) VALUES (?, 'NOTE_ADDED', NULL, NULL, ?, ?, ?, ?)
                """,
                (idea_id, actor, note_type, json.dumps({"note_id": note_id}), now),
            )
        return note_id

    def mark_researched(self, idea_id: int, research: str, *, actor: str = "manual") -> None:
        research = research.strip()
        if not research:
            raise ValueError("Research cannot be empty")
        current = self._get(idea_id)
        if current["status"] == "CAPTURED":
            self.transition(idea_id, "TRIAGED", actor=actor, reason="research started")
        current = self._get(idea_id)
        if current["status"] not in {"TRIAGED", "PARKED"}:
            raise ValueError(f"Cannot mark research from {current['status']}")
        if current["status"] == "PARKED":
            self.transition(idea_id, "TRIAGED", actor=actor, reason="resumed for research")
        self.add_note(idea_id, research, note_type="RESEARCH", actor=actor)
        self.transition(idea_id, "RESEARCHED", actor=actor, reason="research recorded")

    def evaluate(
        self,
        idea_id: int,
        *,
        demand: int,
        feasibility: int,
        strategic_fit: int,
        notes: str = "",
        evaluator: str = "manual",
    ) -> dict[str, object]:
        value = scoring.weighted_score(demand, feasibility, strategic_fit)
        signal = scoring.score_signal(value)
        current = self._get(idea_id)
        if current["status"] == "CAPTURED":
            self.transition(idea_id, "TRIAGED", actor=evaluator, reason="evaluation started")
            current = self._get(idea_id)
        if current["status"] == "PARKED":
            self.transition(idea_id, "TRIAGED", actor=evaluator, reason="resumed for evaluation")
            current = self._get(idea_id)
        if current["status"] not in {"TRIAGED", "RESEARCHED"}:
            raise ValueError(f"Cannot evaluate idea in status {current['status']}")

        now = utc_now()
        with self.con:
            cur = self.con.execute(
                """
                INSERT INTO idea_evaluations(
                    idea_id,demand,feasibility,strategic_fit,weighted_score,signal,notes,evaluator,created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (idea_id, demand, feasibility, strategic_fit, value, signal, notes or None, evaluator, now),
            )
            evaluation_id = int(cur.lastrowid)
            self.con.execute(
                """
                INSERT INTO idea_events(
                    idea_id,event_type,from_status,to_status,actor,reason,metadata_json,created_at
                ) VALUES (?, 'EVALUATED', NULL, NULL, ?, ?, ?, ?)
                """,
                (
                    idea_id,
                    evaluator,
                    signal,
                    json.dumps({"evaluation_id": evaluation_id, "weighted_score": value}),
                    now,
                ),
            )
        self.transition(idea_id, "EVALUATED", actor=evaluator, reason=f"score={value}; signal={signal}")
        return {"evaluation_id": evaluation_id, "weighted_score": value, "signal": signal}

    def get(self, idea_id: int) -> dict[str, object]:
        row = dict(self._get(idea_id))
        evaluation = self.con.execute(
            "SELECT * FROM idea_evaluations WHERE idea_id = ? ORDER BY id DESC LIMIT 1",
            (idea_id,),
        ).fetchone()
        row["latest_evaluation"] = dict(evaluation) if evaluation else None
        return row

    def list(self, *, status: str | None = None, limit: int = 30) -> list[dict[str, object]]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if status:
            rows = self.con.execute(
                "SELECT * FROM ideas WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status.upper(), limit),
            ).fetchall()
        else:
            rows = self.con.execute("SELECT * FROM ideas ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, *, limit: int = 30) -> list[dict[str, object]]:
        query = query.strip()
        if not query:
            return []
        pattern = f"%{query}%"
        rows = self.con.execute(
            """
            SELECT * FROM ideas
            WHERE title LIKE ? COLLATE NOCASE OR body LIKE ? COLLATE NOCASE
            ORDER BY id DESC LIMIT ?
            """,
            (pattern, pattern, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def history(self, idea_id: int) -> list[dict[str, object]]:
        self._get(idea_id)
        rows = self.con.execute(
            "SELECT * FROM idea_events WHERE idea_id = ? ORDER BY id",
            (idea_id,),
        ).fetchall()
        return [dict(row) for row in rows]
