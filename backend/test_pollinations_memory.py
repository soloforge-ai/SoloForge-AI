import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pollinations_image
from character_memory import CharacterMemoryService
from memory import JsonDecisionMemoryStore, JsonEventMemoryStore, MemoryEventName


class PollinationsMemoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.events_path = root / "events.json"
        self.decisions_path = root / "decisions.json"
        self.event_store = JsonEventMemoryStore(self.events_path)
        self.character_memory = CharacterMemoryService(
            JsonDecisionMemoryStore(self.decisions_path)
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _seed_ceo(self):
        self.character_memory.approve_character_dna(
            character_id="ceo",
            version="1.0",
            height_cm=30,
            style="3D Chibi",
            default_outfit="White Luxury Suit; Black shirt; Red tie",
            glasses_required=True,
            wings_allowed=False,
            reason="Approved CEO Character DNA for integration test.",
        )

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

    def test_character_dna_is_injected_into_generation_prompt(self):
        self._seed_ceo()
        response = Mock()
        response.url = "https://example.test/ceo-image"
        response.raise_for_status.return_value = None

        with patch.object(
            pollinations_image,
            "POLLINATIONS_API_KEY",
            "test-key",
        ), patch.object(
            pollinations_image.requests,
            "get",
            return_value=response,
        ) as request_get:
            result = pollinations_image.generate_image(
                {
                    "generation_id": "img-ceo-001",
                    "character_id": "CEO",
                    "prompt": "CEO waves hello in a clean studio.",
                },
                event_store=self.event_store,
                character_memory=self.character_memory,
            )

        sent_prompt = request_get.call_args.kwargs["params"]["prompt"]
        self.assertIn("APPROVED ACTIVE CHARACTER DNA", sent_prompt)
        self.assertIn("Height: 30 cm", sent_prompt)
        self.assertIn("Glasses required: yes", sent_prompt)
        self.assertIn("Wings allowed: no", sent_prompt)
        self.assertIn("Do not generate wings", sent_prompt)
        self.assertEqual(result["character_id"], "ceo")
        self.assertEqual(result["character_dna_version"], "1.0")

        event = self.event_store.retrieve(
            event_name=MemoryEventName.IMAGE_GENERATED,
            entity_id="img-ceo-001",
        )[0]
        self.assertEqual(event.content.metrics["character_id"], "ceo")
        self.assertEqual(event.content.metrics["character_dna_version"], "1.0")

    def test_unknown_character_memory_fails_instead_of_guessing(self):
        with patch.object(
            pollinations_image,
            "POLLINATIONS_API_KEY",
            "test-key",
        ):
            with self.assertRaisesRegex(ValueError, "No ACTIVE Character DNA"):
                pollinations_image.generate_image(
                    {
                        "generation_id": "img-unknown-001",
                        "character_id": "unknown",
                        "prompt": "character portrait",
                    },
                    character_memory=self.character_memory,
                )

    def test_character_id_without_memory_service_preserves_legacy_behavior(self):
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
        ) as request_get:
            result = pollinations_image.generate_image(
                {
                    "generation_id": "img-legacy-character-001",
                    "character_id": "CEO",
                    "prompt": "test prompt",
                }
            )

        sent_prompt = request_get.call_args.kwargs["params"]["prompt"]
        self.assertEqual(sent_prompt, "test prompt")
        self.assertNotIn("character_dna_version", result)

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
