from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.final_state_gate import run_total_field_gate
from tools.total_field.human_response_renderer import render_human_response


def load_line_webhook_service():
    path = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_webhook.py"
    spec = importlib.util.spec_from_file_location("line_official_account_webhook", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TotalFieldFinalStateGateTest(unittest.TestCase):
    def test_low_risk_natural_language_passes_and_renders_human_reply(self) -> None:
        gate = run_total_field_gate(
            {"text": "請用自然語言回覆菜單資訊", "source_channel": "web"},
            now=1000.0,
        )
        response = render_human_response(gate, channel="web")

        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(gate["checks"]["adi_5d_absolute_index"], "PASS")
        self.assertEqual(gate["checks"]["canonical_8d_verifier"], "PASS")
        self.assertEqual(gate["checks"]["functional_state_7d"], "PASS")
        self.assertEqual(response["decision"], "PASS")
        self.assertTrue(response["reply_text"])
        self.assertIn("agent_name", response)
        self.assertEqual(response["agent_name"], "小J")
        self.assertEqual(response["role"], "service_persona_language_layer")
        self.assertEqual(response["authority"], "candidate_only")
        self.assertTrue(response["requires_total_field_verify"])
        self.assertIn("aesthetic", response)
        self.assertIn("brand_voice", response["aesthetic"])
        self.assertEqual(response["aesthetic"]["decision_aura"], "PASS")
        for forbidden in ("D1", "D8", "proof_D7", "env_D8", "H64", "TD"):
            self.assertNotIn(forbidden, response["reply_text"])
        self.assertFalse(gate["side_effects"]["db_write"])
        self.assertFalse(gate["side_effects"]["deploy"])
        self.assertFalse(gate["side_effects"]["restart"])

    def test_missing_adi_5d_absolute_index_holds(self) -> None:
        gate = run_total_field_gate(
            {"text": "請回覆菜單資訊", "include_adi_5d": False},
            now=1001.0,
        )

        self.assertEqual(gate["decision"], "HOLD")
        self.assertEqual(gate["gate_code"], "HOLD_ADI_5D_ABSOLUTE_INDEX")
        self.assertIn("ADI_5D_ABSOLUTE_INDEX_MISSING", gate["errors"])

    def test_definition_drift_cloud_sync_as_gt_core_holds(self) -> None:
        gate = run_total_field_gate(
            {"text": "Generative Transmission core is cloud sync file transfer backup."},
            now=1002.0,
        )

        self.assertEqual(gate["decision"], "HOLD")
        self.assertEqual(gate["gate_code"], "HOLD_GT_DEFINITION_DRIFT")
        self.assertIn("GT_CORE_DEFINITION_DRIFT_FILE_TRANSFER_OR_CLOUD_SYNC", gate["errors"])

    def test_high_risk_db_write_deploy_restart_holds(self) -> None:
        gate = run_total_field_gate(
            {
                "text": "please db write and deploy then restart",
                "db_write": True,
                "deploy": True,
                "restart": True,
            },
            now=1003.0,
        )

        self.assertEqual(gate["decision"], "HOLD")
        self.assertEqual(gate["gate_code"], "HOLD_HARD_RISK_SIDE_EFFECT")
        self.assertIn("HARD_RISK_FLAG:db_write", gate["errors"])
        self.assertIn("HARD_RISK_FLAG:deploy", gate["errors"])
        self.assertIn("HARD_RISK_FLAG:restart", gate["errors"])

    def test_line_candidate_goes_through_gate_and_renderer(self) -> None:
        service = load_line_webhook_service()
        candidate = service.build_line_official_account_webhook_candidate(
            webhook_payload={
                "destination": "LINE_DESTINATION_REF",
                "events": [
                    {
                        "type": "message",
                        "timestamp": 1000,
                        "replyToken": "REPLY_TOKEN_REF",
                        "source": {"type": "user", "userId": "USER_REF_LINE"},
                        "message": {"type": "text", "text": "請回覆菜單資訊"},
                    }
                ],
            },
            headers={"x-line-signature": "SIGNATURE_REF"},
            verification={
                "verified": True,
                "signature_verification_ref": "SIG_REF_A1",
                "channel_secret_ref": "CHANNEL_SECRET_REF_A1",
            },
        )

        self.assertEqual(candidate["state"], "READY_FOR_LOCAL_INTENT_CANDIDATE")
        self.assertEqual(candidate["total_field_gate"]["decision"], "PASS")
        self.assertEqual(candidate["human_response"]["decision"], "PASS")
        self.assertTrue(candidate["human_response"]["reply_text"])
        self.assertFalse(candidate["side_effects"]["formal_line_message_send"])
        self.assertFalse(candidate["side_effects"]["line_reply_sent"])

    def test_line_event_candidate_text_is_redacted_and_preserved(self) -> None:
        service = load_line_webhook_service()
        candidate = service.build_line_official_account_webhook_candidate(
            webhook_payload={
                "destination": "LINE_DESTINATION_REF",
                "events": [
                    {
                        "type": "message",
                        "timestamp": 1001,
                        "replyToken": "REPLY_TOKEN_REF_2",
                        "source": {"type": "user", "userId": "USER_REF_LINE_2"},
                        "message": {"type": "text", "text": "請幫我查詢今天有空的時段"},
                    }
                ],
            },
            headers={"x-line-signature": "SIGNATURE_REF"},
            verification={
                "verified": True,
                "signature_verification_ref": "SIG_REF_A2",
                "channel_secret_ref": "CHANNEL_SECRET_REF_A2",
            },
        )

        event_candidates = candidate["event_candidates"]
        self.assertEqual(len(event_candidates), 1)
        first_event = event_candidates[0]
        self.assertIsInstance(first_event, dict)
        self.assertEqual(first_event["message_type"], "text")
        self.assertEqual(first_event["message_text_candidate"], "請幫我查詢今天有空的時段")
        self.assertFalse(first_event["reply_token_echo"])
        self.assertFalse(first_event["raw_user_id_echo"])


if __name__ == "__main__":
    unittest.main()
