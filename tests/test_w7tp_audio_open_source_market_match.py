import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/total_field/w7tp_audio_open_source_market_match_v1.json"

class AudioOpenSourceMarketMatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_single_authority_boundary(self):
        a = self.data["authority_boundary"]
        self.assertEqual(a["formal_effect_boundary"], "TAIJI01_TOTAL_FIELD")
        self.assertFalse(a["odoo_community_authority"])
        self.assertFalse(a["external_provider_authority"])
        self.assertFalse(a["device_authority"])

    def test_required_candidates_present(self):
        ids = {x["id"] for x in self.data["matched_objects"]}
        required = {
            "MUSIC_ASSISTANT_SERVER",
            "CAMILLA_DSP",
            "OCA_IOT_OCA",
            "OCA_CONNECTOR_COMPONENTS",
            "OCA_QUEUE_JOB",
            "OCA_AUDITLOG",
        }
        self.assertTrue(required.issubset(ids))

    def test_apple_music_provider_is_not_auto_enabled(self):
        ma = next(x for x in self.data["matched_objects"] if x["id"] == "MUSIC_ASSISTANT_SERVER")
        self.assertIn("KEEP_PROVIDER_ACTIVATION_HOLD", ma["risk"])
        self.assertEqual(self.data["install_policy"]["now"], "RESEARCH_AND_BINDING_CANDIDATE_ONLY")

    def test_no_raw_audio_default(self):
        self.assertEqual(
            self.data["founder_intent"]["D6_gst"],
            "TRANSMIT_AUDIO_STATE_REFS_RULES_AND_RECEIPTS_NOT_RAW_AUDIO_BY_DEFAULT",
        )

if __name__ == "__main__":
    unittest.main()
