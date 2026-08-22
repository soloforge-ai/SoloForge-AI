import tempfile
import unittest
from pathlib import Path

from backend.character_memory_bridge import AssetForgeCharacterMemoryBridge


class AssetForgeCharacterMemoryBridgeTests(unittest.TestCase):
    def test_ceo_reads_active_memory_and_builds_prompt_context(self):
        bridge = AssetForgeCharacterMemoryBridge(
            Path(__file__).parent / "data" / "memory" / "decisions.json"
        )

        dna = bridge.resolve("CEO")
        context = bridge.prompt_context("CEO")

        self.assertIsNotNone(dna)
        self.assertEqual(dna.version, "1.0")
        self.assertEqual(dna.height_cm, 30)
        self.assertFalse(dna.wings_allowed)
        self.assertIn("Active DNA version: 1.0", context)
        self.assertIn("Canonical height: 30 cm", context)
        self.assertIn("White Luxury Suit", context)
        self.assertIn("NO wings", context)
        self.assertIn("Glasses are mandatory", context)

    def test_non_seeded_character_keeps_legacy_runtime_path(self):
        bridge = AssetForgeCharacterMemoryBridge(
            Path(__file__).parent / "data" / "memory" / "decisions.json"
        )

        self.assertIsNone(bridge.resolve("Aira"))
        self.assertEqual(bridge.prompt_context("Aira"), "")

    def test_ceo_fails_closed_when_required_memory_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.json"
            bridge = AssetForgeCharacterMemoryBridge(missing)

            with self.assertRaisesRegex(ValueError, "Approved Character DNA is required"):
                bridge.resolve("CEO")


if __name__ == "__main__":
    unittest.main()
