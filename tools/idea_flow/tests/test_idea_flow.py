from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.idea_flow.scoring import score_signal, weighted_score
from tools.idea_flow.service import IdeaFlowService
from tools.idea_flow.telegram import handle_text


class IdeaFlowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "ideas.db"
        self.service = IdeaFlowService(self.db_path)

    def tearDown(self) -> None:
        self.service.close()
        self.tmp.cleanup()

    def test_capture_starts_as_captured_and_records_event(self) -> None:
        idea_id = self.service.capture("Build a founder idea inbox", source="test")
        self.assertEqual(self.service.get(idea_id)["status"], "CAPTURED")
        history = self.service.history(idea_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["event_type"], "CAPTURED")

    def test_valid_transition_records_history(self) -> None:
        idea_id = self.service.capture("Idea")
        self.service.transition(idea_id, "TRIAGED", actor="test", reason="reviewed")
        self.assertEqual(self.service.get(idea_id)["status"], "TRIAGED")
        self.assertEqual(len(self.service.history(idea_id)), 2)

    def test_invalid_transition_fails_service_level(self) -> None:
        idea_id = self.service.capture("Idea")
        with self.assertRaises(ValueError):
            self.service.transition(idea_id, "GRADUATED", actor="test")

    def test_invalid_transition_fails_database_level(self) -> None:
        idea_id = self.service.capture("Idea")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.service.con:
                self.service.con.execute("UPDATE ideas SET status='GRADUATED' WHERE id=?", (idea_id,))

    def test_evaluation_auto_triages_and_moves_to_evaluated(self) -> None:
        idea_id = self.service.capture("Idea")
        result = self.service.evaluate(
            idea_id,
            demand=4,
            feasibility=5,
            strategic_fit=5,
            evaluator="test",
        )
        self.assertEqual(result["weighted_score"], 4.55)
        self.assertEqual(result["signal"], "GRADUATE_CANDIDATE")
        self.assertEqual(self.service.get(idea_id)["status"], "EVALUATED")

    def test_graduate_requires_evaluation(self) -> None:
        idea_id = self.service.capture("Idea")
        self.service.transition(idea_id, "TRIAGED", actor="test")
        with self.assertRaises(ValueError):
            self.service.transition(idea_id, "GRADUATED", actor="test")

    def test_experiment_lifecycle(self) -> None:
        idea_id = self.service.capture("Idea")
        self.service.evaluate(idea_id, demand=5, feasibility=5, strategic_fit=5)
        self.service.transition(idea_id, "GRADUATED")
        self.service.transition(idea_id, "EXPERIMENT")
        self.service.transition(idea_id, "VALIDATED")
        self.assertEqual(self.service.get(idea_id)["status"], "VALIDATED")

    def test_park_and_resume(self) -> None:
        idea_id = self.service.capture("Idea")
        self.service.transition(idea_id, "PARKED")
        self.service.transition(idea_id, "TRIAGED")
        self.assertEqual(self.service.get(idea_id)["status"], "TRIAGED")

    def test_research_note_and_state(self) -> None:
        idea_id = self.service.capture("Idea")
        self.service.mark_researched(idea_id, "Found three competitors", actor="test")
        self.assertEqual(self.service.get(idea_id)["status"], "RESEARCHED")
        row = self.service.con.execute(
            "SELECT note_type, body FROM idea_notes WHERE idea_id=?", (idea_id,)
        ).fetchone()
        self.assertEqual(row["note_type"], "RESEARCH")

    def test_search(self) -> None:
        self.service.capture("Novel quote engine")
        self.service.capture("Sticker maker")
        rows = self.service.search("quote")
        self.assertEqual(len(rows), 1)
        self.assertIn("quote", rows[0]["body"].lower())

    def test_score_validation(self) -> None:
        with self.assertRaises(ValueError):
            weighted_score(6, 5, 5)
        self.assertEqual(score_signal(2.99), "REJECT_CANDIDATE")
        self.assertEqual(score_signal(3.0), "PARK_OR_REVIEW")
        self.assertEqual(score_signal(4.0), "GRADUATE_CANDIDATE")

    def test_migration_is_idempotent(self) -> None:
        self.service.close()
        self.service = IdeaFlowService(self.db_path)
        self.service.close()
        self.service = IdeaFlowService(self.db_path)
        count = self.service.con.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        self.assertEqual(count, 1)

    def test_telegram_plain_text_captures(self) -> None:
        reply = handle_text(self.service, "ไอเดียทำ quote engine", actor="telegram:test")
        self.assertIn("Idea #1", reply)
        self.assertEqual(self.service.get(1)["status"], "CAPTURED")


if __name__ == "__main__":
    unittest.main()
