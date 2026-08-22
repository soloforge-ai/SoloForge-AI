import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pollinations_image
from memory import JsonEventMemoryStore, MemoryEventName


class PollinationsMemoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.events_path = Path(self.temp_dir.name) / "events.json"
        self.event_store = JsonEventMemoryStore(self.events_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_success_emits_image_generated_event(self):
        response = Mock()
        response.url = "https://example.test/generated-image"
        response.raise_for_status.return_value = None

        payload = {
            "generation_id": "img-test-001",
            "task_id": "task-001",
            "prompt": "clean product hero image",
            "model": "gpt-image-2",
            "width": 1024,
            "height": 1280,
        }

        with patch.object(
            pollinations_image,
            "POLLINATIONS_API_KEY",
            "test-key",
        ), patch.object(
            pollinations_image.requests,
            "get",
            return_value=response,
        ):
            result = pollinations_image.generate_image(
                payload,
                event_store=self.event_store,
            )

        self.assertEqual(result["generation_id"], "img-test-001")
        events = self.event_store.retrieve(
            event_name=MemoryEventName.IMAGE_GENERATED,
            entity_id="img-test-001",
        )
        self.assertEqual(len(events), 1)

        event = events[0]
        self.assertEqual(event.content.result, "success")
        self.assertEqual(event.content.provider, "pollinations")
        self.assertEqual(event.content.model, "gpt-image-2")
        self.assertEqual(event.content.task_id, "task-001")
        self.assertEqual(
            event.content.output_refs,
            ["https://example.test/generated-image"],
        )
        self.assertEqual(event.content.metrics["width"], 1024)
        self.assertEqual(event.content.metrics["height"], 1280)

    def test_failure_emits_error_event_and_preserves_exception(self):
        payload = {
            "generation_id": "img-test-002",
            "prompt": "test prompt",
        }

        with patch.object(
            pollinations_image,
            "POLLINATIONS_API_KEY",
            None,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "POLLINATIONS_API_KEY is not configured",
            ):
                pollinations_image.generate_image(
                    payload,
                    event_store=self.event_store,
                )

        events = self.event_store.retrieve(
            event_name=MemoryEventName.ERROR_OCCURRED,
            entity_id="img-test-002",
        )
        self.assertEqual(len(events), 1)

        event = events[0]
        self.assertEqual(event.content.result, "failed")
        self.assertEqual(event.content.error["type"], "RuntimeError")
        self.assertIn(
            "POLLINATIONS_API_KEY is not configured",
            event.content.error["message"],
        )

    def test_existing_caller_without_event_store_still_works(self):
        response = Mock()
        response.url = "https://example.test/generated-image"
        response.raise_for_status.return_value = None

        with patch.object(
            pollinations_image,
            "POLLINATIONS_API_KEY",
            "test-key",
        ), patch.object(
            pollinations_image.requests,
            "get",
            return_value=response,
        ):
            result = pollinations_image.generate_image(
                {
                    "generation_id": "img-test-003",
                    "prompt": "test prompt",
                }
            )

        self.assertEqual(result["generation_id"], "img-test-003")
        self.assertFalse(self.events_path.exists())


if __name__ == "__main__":
    unittest.main()
