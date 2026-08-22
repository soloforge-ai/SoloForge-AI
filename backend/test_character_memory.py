import tempfile
import unittest
from pathlib import Path

from character_memory import CharacterMemoryService
from memory import JsonDecisionMemoryStore, MemoryStatus


class CharacterMemoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = JsonDecisionMemoryStore(Path(self.temp_dir.name) / "decisions.json")
        self.service = CharacterMemoryService(self.store)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_approve_and_retrieve_ceo_character_dna(self):
        self.service.approve_character_dna(
            character_id="ceo",
            version="1.0",
            height_cm=30,
            style="3D Chibi",
            default_outfit="White Luxury Suit; Black shirt; Red tie; White pants; Black Leather shoes; Gold SoloForge Pin",
            glasses_required=True,
            wings_allowed=False,
            reason="Seeded from approved CEO character profile.",
        )

        dna = self.service.retrieve_character_dna("CEO")

        self.assertIsNotNone(dna)
        self.assertEqual(dna.character_id, "ceo")
        self.assertEqual(dna.version, "1.0")
        self.assertEqual(dna.height_cm, 30)
        self.assertEqual(dna.style, "3D Chibi")
        self.assertTrue(dna.glasses_required)
        self.assertFalse(dna.wings_allowed)

    def test_new_character_version_supersedes_old_values(self):
        common = dict(
            character_id="ceo",
            height_cm=30,
            style="3D Chibi",
            default_outfit="White Luxury Suit; Black shirt; Red tie",
            glasses_required=True,
            wings_allowed=False,
        )
        self.service.approve_character_dna(
            **common,
            version="1.0",
            reason="Initial approved CEO DNA.",
        )
        self.service.approve_character_dna(
            **common,
            version="1.1",
            reason="Approved CEO DNA revision.",
        )

        dna = self.service.retrieve_character_dna("ceo")
        self.assertEqual(dna.version, "1.1")

        version_records = [
            record
            for record in self.store.list_all()
            if record.content.decision_key == "character.ceo.active_version"
        ]
        self.assertEqual(len(version_records), 2)
        self.assertEqual(version_records[0].status, MemoryStatus.SUPERSEDED)
        self.assertEqual(version_records[1].status, MemoryStatus.ACTIVE)
        self.assertEqual(version_records[1].supersedes, version_records[0].id)

    def test_unknown_character_returns_none(self):
        self.assertIsNone(self.service.retrieve_character_dna("aira"))

    def test_partial_character_dna_surfaces_conflict_instead_of_guessing(self):
        self.store.approve(
            subject="character.ceo.height_cm",
            decision_key="character.ceo.height_cm",
            decision="30",
            reason="Partial test record.",
            scope="ceo",
        )

        with self.assertRaisesRegex(ValueError, "Incomplete Character DNA"):
            self.service.retrieve_character_dna("ceo")


if __name__ == "__main__":
    unittest.main()
