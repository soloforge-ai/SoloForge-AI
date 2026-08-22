import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from memory import (
    JsonDecisionMemoryStore,
    JsonEventMemoryStore,
    MemoryEventName,
    MemoryStatus,
)
import pollinations_image


class MemoryFoundationEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.decision_store = JsonDecisionMemoryStore(root / "decisions.json")
        self.event_store = JsonEventMemoryStore(root / "events.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_decision_drives_generation_and_runtime_event_is_retrievable(self):
        approved = self.decision_store.approve(
            subject="image.provider.default",
            decision_key="image.provider.default",
            decision="pollinations",
            reason="Approved provider for the first Memory Foundation integration.",
        )

        active = self.decision_store.retrieve_active(
            decision_key="image.provider.default"
        )
        self.assertIsNotNone(active)
        self.assertEqual(active.id, approved.id)
        self.assertEqual(active.status, MemoryStatus.ACTIVE)
        self.assertEqual(active.content.decision, "pollinations")

        response = Mock()
        response.url = "https://example.test/generated/image-001.png"
        response.raise_for_status.return_value = None

        payload = {
            "generation_id": "image-001",
            "task_id": "task-e2e-001",
            "prompt": "SoloForge memory foundation test image",
            "model": "gpt-image-2",
            "width": 1024,
            "height": 1024,
        }

        with patch.object(pollinations_image, "POLLINATIONS_API_KEY", "test-key"), patch.object(
            pollinations_image.requests,
            "get",
            return_value=response,
        ):
            result = pollinations_image.generate_image(
                payload,
                event_store=self.event_store,
            )

        self.assertEqual(result["generation_id"], "image-001")
        self.assertEqual(result["url"], response.url)

        events = self.event_store.retrieve(
            event_name=MemoryEventName.IMAGE_GENERATED,
            entity_type="image_generation",
            entity_id="image-001",
        )

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.status, MemoryStatus.ACTIVE)
        self.assertEqual(event.content.result, "success")
        self.assertEqual(event.content.task_id, "task-e2e-001")
        self.assertEqual(event.content.provider, "pollinations")
        self.assertEqual(event.content.model, "gpt-image-2")
        self.assertEqual(event.content.output_refs, [response.url])

    def test_superseded_decision_does_not_destroy_runtime_history(self):
        first = self.decision_store.approve(
            subject="image.provider.default",
            decision_key="image.provider.default",
            decision="pollinations",
            reason="Initial provider decision.",
        )

        self.event_store.append(
            event_name=MemoryEventName.IMAGE_GENERATED,
            actor="pollinations_image",
            entity_type="image_generation",
            entity_id="image-history-001",
            result="success",
            provider="pollinations",
            model="gpt-image-2",
        )

        second = self.decision_store.approve(
            subject="image.provider.default",
            decision_key="image.provider.default",
            decision="future-provider",
            reason="Replacement provider approved for a later phase.",
        )

        decisions = self.decision_store.list_all()
        first_after = next(item for item in decisions if item.id == first.id)
        second_after = next(item for item in decisions if item.id == second.id)

        self.assertEqual(first_after.status, MemoryStatus.SUPERSEDED)
        self.assertEqual(second_after.status, MemoryStatus.ACTIVE)
        self.assertEqual(second_after.supersedes, first.id)

        active = self.decision_store.retrieve_active(
            decision_key="image.provider.default"
        )
        self.assertEqual(active.content.decision, "future-provider")

        historical_events = self.event_store.retrieve(
            event_name=MemoryEventName.IMAGE_GENERATED,
            entity_id="image-history-001",
        )
        self.assertEqual(len(historical_events), 1)
        self.assertEqual(historical_events[0].content.provider, "pollinations")


if __name__ == "__main__":
    unittest.main()
