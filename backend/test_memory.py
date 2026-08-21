import json
import tempfile
import unittest
from pathlib import Path

from memory import JsonDecisionMemoryStore, MemoryStatus


class DecisionMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "decisions.json"
        self.store = JsonDecisionMemoryStore(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_approve_and_retrieve_active_decision(self):
        created = self.store.approve(
            subject="brand.primary_mascot",
            decision_key="brand.primary_mascot",
            decision="CEO",
            reason="Approved as primary mascot.",
        )

        active = self.store.retrieve_active(
            decision_key="brand.primary_mascot"
        )

        self.assertIsNotNone(active)
        self.assertEqual(active.id, created.id)
        self.assertEqual(active.status, MemoryStatus.ACTIVE)
        self.assertEqual(active.content.decision, "CEO")
        self.assertEqual(active.source, "human_approval")

    def test_new_decision_supersedes_previous_without_deleting_history(self):
        first = self.store.approve(
            subject="brand.primary_mascot",
            decision_key="brand.primary_mascot",
            decision="Puri",
            reason="Initial approved mascot.",
        )

        second = self.store.approve(
            subject="brand.primary_mascot",
            decision_key="brand.primary_mascot",
            decision="CEO",
            reason="CEO is now the approved primary mascot.",
        )

        records = self.store.list_all()
        first_after = next(record for record in records if record.id == first.id)
        second_after = next(record for record in records if record.id == second.id)

        self.assertEqual(len(records), 2)
        self.assertEqual(first_after.status, MemoryStatus.SUPERSEDED)
        self.assertEqual(second_after.status, MemoryStatus.ACTIVE)
        self.assertEqual(second_after.supersedes, first.id)

        active = self.store.retrieve_active(
            decision_key="brand.primary_mascot"
        )
        self.assertEqual(active.id, second.id)
        self.assertEqual(active.content.decision, "CEO")

    def test_scope_keeps_parallel_decisions_separate(self):
        self.store.approve(
            subject="prompt.style",
            decision_key="prompt.style",
            decision="clean",
            reason="Default product prompt style.",
            scope="product",
        )
        self.store.approve(
            subject="prompt.style",
            decision_key="prompt.style",
            decision="cinematic",
            reason="Default story prompt style.",
            scope="story",
        )

        product = self.store.retrieve_active(
            decision_key="prompt.style",
            scope="product",
        )
        story = self.store.retrieve_active(
            decision_key="prompt.style",
            scope="story",
        )

        self.assertEqual(product.content.decision, "clean")
        self.assertEqual(story.content.decision, "cinematic")

    def test_non_owner_cannot_create_authoritative_active_decision(self):
        with self.assertRaises(ValueError):
            self.store.approve(
                subject="architecture.storage",
                decision_key="architecture.storage",
                decision="graph-db",
                reason="Agent preference.",
                authority="agent",
            )

    def test_store_is_valid_readable_json(self):
        self.store.approve(
            subject="brand.primary_mascot",
            decision_key="brand.primary_mascot",
            decision="CEO",
            reason="Approved as primary mascot.",
        )

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["status"], "ACTIVE")
        self.assertEqual(
            payload[0]["content"]["decision_key"],
            "brand.primary_mascot",
        )


if __name__ == "__main__":
    unittest.main()
