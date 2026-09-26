import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"configs/total_field/w7tp_xiaoj_organization_av_ai_v1.json"

class XiaoJOrganizationAVAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(P.read_text(encoding="utf-8"))

    def test_product_is_organization_ai(self):
        p=self.data["product_identity"]
        self.assertEqual(p["class"],"ORGANIZATION_AI")
        self.assertTrue(p["not_personal_assistant_only"])
        self.assertTrue(p["not_single_player_app"])

    def test_scene_control_contains_music(self):
        effects=set(self.data["scene_control_contract"]["preauthorized_effects"])
        self.assertIn("PLAY_MUSIC",effects)
        self.assertIn("SET_ZONE_VOLUME",effects)
        self.assertIn("SELECT_AUDIO_SCENE",effects)
        self.assertIn("RESTORE_PREVIOUS_SCENE",effects)

    def test_bounded_scene_effects_can_execute(self):
        self.assertTrue(
            self.data["scene_control_contract"]["bounded_reversible_effects_may_execute_when_preauthorized"]
        )

    def test_member_sovereignty_preserved(self):
        a=self.data["authority_boundary"]
        self.assertTrue(a["natural_person_sovereignty_preserved"])
        self.assertTrue(a["member_consent_not_inferred_from_org_policy"])

    def test_odoo_is_not_authority(self):
        self.assertFalse(self.data["authority_boundary"]["odoo_community_authority"])

if __name__=="__main__":
    unittest.main()
