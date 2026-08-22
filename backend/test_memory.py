import json
import tempfile
import unittest
from pathlib import Path

from memory import (
    JsonDecisionMemoryStore,
    JsonEventMemoryStore,
    MemoryEventName,
    MemoryStatus,
)


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


class EventMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "events.json"
        self.store = JsonEventMemoryStore(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_append_event_and_preserve_payload(self):
        event = self.store.append(
            event_name=MemoryEventName.IMAGE_GENERATED,
            actor="ai_forge",
            entity_type="generation",
            entity_id="gen-001",
            result="success",
            model="flux",
            provider="pollinations",
            output_refs=["asset://gen-001.png"],
            duration_ms=1250,
        )

        self.assertEqual(event.type, "event")
        self.assertEqual(event.status, MemoryStatus.ACTIVE)
        self.assertEqual(event.content.event_name, MemoryEventName.IMAGE_GENERATED)
        self.assertEqual(event.content.provider, "pollinations")
        self.assertEqual(event.content.duration_ms, 1250)

    def test_events_are_append_only(self):
        first = self.store.append(
            event_name=MemoryEventName.IMAGE_GENERATED,
            actor="ai_forge",
            entity_type="generation",
            entity_id="gen-001",
            result="success",
        )
        second = self.store.append(
            event_name=MemoryEventName.OUTPUT_ACCEPTED,
            actor="project_owner",
            entity_type="generation",
            entity_id="gen-001",
            result="accepted",
        )

        records = self.store.list_all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].id, first.id)
        self.assertEqual(records[1].id, second.id)
        self.assertEqual(records[0].status, MemoryStatus.ACTIVE)
        self.assertEqual(records[1].status, MemoryStatus.ACTIVE)

    def test_retrieve_filters_by_event_and_entity(self):
        self.store.append(
            event_name=MemoryEventName.IMAGE_GENERATED,
            actor="ai_forge",
            entity_type="generation",
            entity_id="gen-001",
            result="success",
        )
        self.store.append(
            event_name=MemoryEventName.IMAGE_GENERATED,
            actor="ai_forge",
            entity_type="generation",
            entity_id="gen-002",
            result="success",
        )
        self.store.append(
            event_name=MemoryEventName.ERROR_OCCURRED,
            actor="ai_forge",
            entity_type="generation",
            entity_id="gen-002",
            result="failed",
            error={"code": "TIMEOUT"},
        )

        generated = self.store.retrieve(
            event_name=MemoryEventName.IMAGE_GENERATED,
            entity_type="generation",
        )
        gen_002 = self.store.retrieve(entity_id="gen-002")

        self.assertEqual(len(generated), 2)
        self.assertEqual(len(gen_002), 2)
        self.assertTrue(
            any(
                item.content.event_name == MemoryEventName.ERROR_OCCURRED
                for item in gen_002
            )
        )

    def test_event_store_serializes_enum_as_plain_json(self):
        self.store.append(
            event_name=MemoryEventName.PROMPT_GENERATED,
            actor="prompt_engine",
            entity_type="prompt",
            entity_id="prompt-001",
            result="success",
            metrics={"tokens": 420},
        )

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(payload[0]["type"], "event")
        self.assertEqual(payload[0]["status"], "ACTIVE")
        self.assertEqual(
            payload[0]["content"]["event_name"],
            "PROMPT_GENERATED",
        )
        self.assertEqual(payload[0]["content"]["metrics"]["tokens"], 420)

    def test_rejects_invalid_event_fields(self):
        with self.assertRaises(ValueError):
            self.store.append(
                event_name=MemoryEventName.ERROR_OCCURRED,
                actor="",
                entity_type="generation",
                entity_id="gen-003",
                result="failed",
            )

        with self.assertRaises(ValueError):
            self.store.append(
                event_name=MemoryEventName.IMAGE_GENERATED,
                actor="ai_forge",
                entity_type="generation",
                entity_id="gen-003",
                result="success",
                duration_ms=-1,
            )


if __name__ == "__main__":
    unittest.main()
