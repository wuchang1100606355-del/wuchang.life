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

    def test_capability_query_passes_and_reply_reflects_capability(self) -> None:
        gate = run_total_field_gate(
            {"text": "你能幫我做什麼？"},
            now=1002.5,
        )
        response = render_human_response(gate, channel="web")

        self.assertEqual(gate["decision"], "PASS")
        self.assertTrue(
            "能力" in response["reply_text"]
            or "幫你做" in response["reply_text"]
            or "可核對" in response["reply_text"]
        )

    def test_any_question_query_stays_candidate_only_and_boundaried(self) -> None:
        gate = run_total_field_gate(
            {"text": "你能回答任何問題嗎？"},
            now=1002.2,
        )
        response = render_human_response(gate, channel="web")

        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(response["decision"], "PASS")
        self.assertIn("候選", response["reply_text"])
        self.assertIn("正式", response["reply_text"])
        self.assertFalse(response["line_reply_sent"])
        self.assertFalse(response["formal_send_executed"])

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

    def test_payment_term_holds_without_flags(self) -> None:
        gate = run_total_field_gate(
            {"text": "幫我付款"},
            now=1004.0,
        )

        self.assertEqual(gate["decision"], "HOLD")
        self.assertEqual(gate["gate_code"], "HOLD_HARD_RISK_SIDE_EFFECT")
        self.assertIn("HARD_RISK_TERM:付款", gate["errors"])

    def test_detour_alert_hard_gate_blocks_reconstruction_bypass(self) -> None:
        gate = run_total_field_gate(
            {
                "text": "old Codex thread context window full; cafe business onboarding detoured into restore flow",
                "source_channel": "web",
                "target_packet": "cafe_business_onboarding",
                "actual_packet": "packet_inference_cockpit",
                "allowed_paths": ["Taiji_Odoo/addons/wuchang_cafe_ai_gateway/"],
                "touched_paths": ["web/packet_inference_cockpit/app.js"],
                "task_layer": "backend",
                "added_features": ["UI", "AI key", "cloud translator", "literary flow", "scenario deck"],
                "restore_requested": True,
                "diff_ownership_verified": False,
                "pass_exists": True,
                "rerun_requested": True,
                "min_landing_required": True,
                "architecture_expansion": True,
                "user_operation_burden_increased": True,
                "required_mode": "generative_reconstruction",
                "actual_mode": "restore",
            },
            now=1004.5,
        )

        self.assertEqual(gate["decision"], "BLOCK")
        self.assertEqual(gate["gate_code"], "BLOCK_DETOUR_ALERT_HARD_GATE")
        self.assertEqual(gate["risk_level"], "CRITICAL")
        self.assertEqual(gate["checks"]["detour_alert_hard_gate"], "FAIL")
        expected_alerts = {
            "CONTEXT_WINDOW_FULL",
            "TARGET_PACKET_MISMATCH",
            "TOUCHED_OUT_OF_SCOPE_PATH",
            "BACKEND_TASK_TOUCHED_FRONTEND",
            "CAFE_ONBOARDING_TOUCHED_COCKPIT_UI",
            "UNAUTHORIZED_FEATURE_EXPANSION",
            "RESTORE_WITHOUT_DIFF_OWNERSHIP",
            "PASS_EXISTS_BUT_RERUN_REQUESTED",
            "MIN_LANDING_BUT_REPORT_OR_ARCHITECTURE_EXPANSION",
            "USER_OPERATION_BURDEN_INCREASED",
            "NON_GENERATIVE_RECONSTRUCTION_PATH",
        }
        self.assertTrue(expected_alerts.issubset(set(gate["errors"])))
        self.assertEqual(set(gate["detour_alert_hard_gate"]["alerts"]), expected_alerts)

    def test_paste_burden_when_reconstructable_holds_detour_alert(self) -> None:
        gate = run_total_field_gate(
            {
                "text": "助手要求把這段貼回來，但 RUN_ID / TESTS / GIT_STATUS 和現有 diff 已可重構",
                "assistant_request": "請貼給 Codex，再貼一次到新 thread，重跑給我看",
                "run_id": "RUN_ID=TOTAL_FIELD_GATE_EXAMPLE",
                "tests": "TESTS=PASS",
                "git_status": "GIT_STATUS=dirty",
                "diff_summary": "current diff reconstructable",
                "total_field_can_decide": True,
                "generative_reconstruction_available": True,
            },
            now=1004.7,
        )

        self.assertEqual(gate["state"], "HOLD_DETOUR_ALERT")
        self.assertEqual(gate["decision"], "HOLD")
        self.assertEqual(gate["gate_code"], "HOLD_DETOUR_ALERT")
        self.assertIn("PASTE_BURDEN_WHEN_RECONSTRUCTABLE", gate["errors"])
        alert = gate["detour_alert_hard_gate"]
        self.assertEqual(alert["STATE"], "HOLD_DETOUR_ALERT")
        self.assertEqual(alert["REASON"], "PASTE_BURDEN_WHEN_RECONSTRUCTABLE")
        self.assertEqual(alert["RULE"], "凡可不貼而要使用者貼，即為繞路")
        self.assertEqual(
            alert["REQUIRED_PATH"],
            "SOURCE → PACKET → RECONSTRUCT → VERIFY → TOTAL_FIELD_DECIDES → SEAL/HOLD",
        )
        self.assertEqual(alert["NEXT"], "改由總場/現有證據/生成式重構判斷，不再要求使用者搬運")

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
